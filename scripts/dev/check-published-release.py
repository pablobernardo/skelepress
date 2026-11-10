#!/usr/bin/env python3
"""Verify real published assets and installed CLIs in a disposable hosted CI VM."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import runpy
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
# Reuse the reviewed HTTPS/TLS redirect policy, without running candidate acceptance.
SUPPORT = runpy.run_path(str(ROOT / "scripts/dev/check-release-candidate.py"))
require, fetch, digest = (SUPPORT[name] for name in ("require", "fetch", "digest"))
ALIASES = {f"skelepress_{system}_{arch}.tar.gz"
           for system in ("darwin", "linux") for arch in ("amd64", "arm64")}


def checksums(raw):
    rows = [line.split() for line in raw.decode().splitlines()]
    require(all(len(row) == 2 and re.fullmatch(r"[0-9a-f]{64}", row[0]) for row in rows),
            "Malformed published checksums")
    result = {name: value for value, name in rows}
    require(len(result) == len(rows) and set(result) == ALIASES, "Unexpected checksum entries")
    return result


def archive_files(path):
    result, names = {}, set()
    with tarfile.open(path) as archive:
        for member in archive.getmembers():
            name = PurePosixPath(member.name)
            require(not name.is_absolute() and ".." not in name.parts and "\\" not in member.name
                    and str(name) not in names and (member.isfile() or member.isdir()),
                    "Unsafe or duplicate archive member")
            names.add(str(name))
            if member.isfile():
                stream = archive.extractfile(member)
                if stream is None:
                    raise RuntimeError("Published payload member has no data")
                with stream:
                    result[str(name)] = (hashlib.sha256(stream.read()).hexdigest(), member.mode & 0o777)
    require("bin/skelepress" in result and "VERSION" in result, "Incomplete published payload")
    return result


def snapshot(root):
    return {str(path.relative_to(root)): (digest(path), path.stat().st_mode & 0o777)
            for path in root.rglob("*") if path.is_file()}


def accept(args, out):
    commands = []

    def run(argv, env=None):
        try:
            result = subprocess.run([str(a) for a in argv], env=env, cwd=ROOT,
                                    capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired as exc:
            result = subprocess.CompletedProcess(argv, 124, exc.stdout or b"", exc.stderr or b"")
        index = len(commands)
        for field in ("stdout", "stderr"):
            value = getattr(result, field)
            (out / f"{index:02d}.{field}").write_text(
                value.decode(errors="replace") if isinstance(value, bytes) else value)
        commands.append({"args": [str(a) for a in argv], "exit_code": result.returncode,
                         "stdout": f"{index:02d}.stdout", "stderr": f"{index:02d}.stderr"})
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        require(result.returncode == 0, f"Command {index} failed with exit {result.returncode}")
        return result.stdout.decode(errors="replace") if isinstance(result.stdout, bytes) else result.stdout

    repo = os.environ["GITHUB_REPOSITORY"]
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo), "Invalid repository")
    api = f"https://api.github.com/repos/{repo}/releases"

    def release(suffix, expected, label):
        data = SUPPORT["parse_json"](fetch(f"{api}/{suffix}"))
        (out / f"{label}-release.json").write_text(json.dumps(data, indent=2) + "\n")
        require(data.get("tag_name") == expected and not data.get("draft")
                and not data.get("prerelease"), "Published stable tag differs from requested tag")
        return data

    latest = release("latest", args.tag, "latest")
    previous = release(f"tags/{args.baseline_tag}", args.baseline_tag, "baseline")
    native = f"skelepress_linux_{'arm64' if platform.machine() in ('aarch64', 'arm64') else 'amd64'}.tar.gz"
    for label, data in (("published", latest), ("baseline", previous)):
        assets = data["assets"]
        urls = {asset["name"]: asset["browser_download_url"] for asset in assets}
        require(len(urls) == len(assets) and set(urls) == ALIASES | {"checksums.txt"},
                "Unexpected published assets")
        folder = out / label
        folder.mkdir()
        raw = fetch(urls["checksums.txt"])
        (folder / "checksums.txt").write_bytes(raw)
        sums = checksums(raw)
        for name in sorted(ALIASES if label == "published" else {native}):
            path = folder / name
            path.write_bytes(fetch(urls[name]))
            require(digest(path) == sums[name], "Published archive checksum mismatch")
            if label == "published":
                require(sums[name] == args.checksum, "Published asset differs from approved candidate")
    expected_files = archive_files(out / "published" / native)
    baseline_files = archive_files(out / "baseline" / native)
    with tempfile.TemporaryDirectory(prefix="skelepress-published-", dir=os.environ["RUNNER_TEMP"]) as temporary:
        work = Path(temporary)
        source = work / "source"
        run(["git", "clone", "--depth", "1", "--branch", args.tag, f"https://github.com/{repo}.git", source])
        require(run(["git", "-C", source, "rev-parse", "HEAD"]).strip() == args.sha,
                "Published tag does not resolve to approved SHA")
        tree = run(["git", "-C", source, "rev-parse", "HEAD^{tree}"]).strip()
        require((source / "VERSION").read_text() == args.tag[1:] + "\n", "Wrong source VERSION")

        def environment(label):
            home = work / label
            for directory in (home, home / "tmp", home / "cache"):
                directory.mkdir(parents=True, exist_ok=True)
            env = os.environ.copy()
            env.update(HOME=str(home), TMPDIR=str(home / "tmp"), XDG_CACHE_HOME=str(home / "cache"),
                       PYTHONDONTWRITEBYTECODE="1", SKELEPRESS_LANG="en",
                       SKELEPRESS_INSTALL_HOME=str(home / "managed"),
                       SKELEPRESS_UPDATE_HOME=str(home / "managed"), SKELEPRESS_INSTALL_DIR=str(home / "bin"),
                       SKELEPRESS_RELEASE_API_BASE=api, SKELEPRESS_UPDATE_API_BASE=api,
                       SKELEPRESS_UPDATE_LOG_FILE=str(out / f"{label}-update.log"))
            return env, home / "bin/skelepress", home / "managed/current"

        def version(cli, env, tag):
            require(run([cli, "--version"], env) == f"skelepress {tag[1:]}\n", "Wrong installed version")
            require(not (out / commands[-1]["stderr"]).read_text(), "Version command wrote stderr")

        clean_env, clean_cli, clean_current = environment("clean")
        run(["bash", source / "scripts/delivery/install.sh"], clean_env)
        version(clean_cli, clean_env, args.tag)
        require(clean_current.resolve() == clean_current.parent / "versions" / args.tag
                and clean_cli.resolve() == clean_current.resolve() / "bin/skelepress"
                and snapshot(clean_current.resolve()) == expected_files,
                "Clean install differs from approved published payload")
        upgrade_env, upgrade_cli, current = environment("upgrade")
        baseline = current.parent / "versions" / args.baseline_tag
        baseline.mkdir(parents=True)
        upgrade_cli.parent.mkdir()
        run(["tar", "-xzf", out / "baseline" / native, "-C", baseline])
        current.symlink_to(baseline)
        upgrade_cli.symlink_to(current / "bin/skelepress")
        version(upgrade_cli, upgrade_env, args.baseline_tag)
        old_pointer, old_binary = os.readlink(current), os.readlink(upgrade_cli)
        require(snapshot(baseline) == baseline_files, "Baseline differs from verified published archive")
        check = run([upgrade_cli, "update", "--check"], upgrade_env)
        require(args.tag[1:] in check and args.baseline_tag[1:] in check, "Update check omitted versions")
        require(os.readlink(current) == old_pointer and os.readlink(upgrade_cli) == old_binary
                and snapshot(baseline) == baseline_files, "Update check changed managed state")
        run([upgrade_cli, "update", "--yes"], upgrade_env)
        version(upgrade_cli, upgrade_env, args.tag)
        require(current.resolve() == baseline.parent / args.tag and os.readlink(upgrade_cli) == old_binary
                and snapshot(current.resolve()) == expected_files and snapshot(baseline) == baseline_files,
                "Upgrade changed baseline or installed wrong payload")
        chapters = work / "chapters"
        chapters.mkdir()
        (chapters / "smoke.md").write_text("# Published release smoke\n\nInstalled archive renders real PDF.\n")
        config = {
            "version": 1, "project": {"name": "published-smoke", "base_dir": str(work)},
            "document": {"title": "Published smoke", "language": "en", "titlepage": False},
            "input": {"chapters_dir": "chapters", "glob": "*.md", "order": "natural", "explicit_files": ["smoke.md"]},
            "output": {"dir": "pdf", "file_prefix": "published", "suffix": "smoke", "keep_merged_markdown": True},
            "pandoc": {"pdf_engine": "xelatex", "toc": False, "toc_depth": 3,
                       "number_sections": False, "resource_path": ["."]},
            "filters": {"emoji": {"enabled": False}, "mermaid": {"enabled": False}, "extra_lua_filters": []},
            "runtime": {"required_commands": ["pandoc", "xelatex"], "strict": True},
            "compat": {"legacy_clearpage_between_h1": False}}
        config_path = work / "config.json"
        for label, cli, env in (("clean", clean_cli, clean_env), ("upgrade", upgrade_cli, upgrade_env)):
            config["output"]["dir"] = f"pdf-{label}"
            config_path.write_text(json.dumps(config))
            for command in ("info", "validate-config", "doctor", "render"):
                argv = [cli, "info", "--json"] if command == "info" else [cli, command, "-c", config_path]
                run(argv, env)
            pdfs = list((work / f"pdf-{label}").glob("*.pdf"))
            require(len(pdfs) == 1 and pdfs[0].read_bytes().startswith(b"%PDF-"), "Missing smoke PDF")
            target = out / f"{label}-smoke.pdf"
            target.write_bytes(pdfs[0].read_bytes())
            require("Installed archive renders real PDF." in run(["pdftotext", target, "-"]), "Wrong PDF text")
        release("latest", args.tag, "final-latest")
        require(run(["git", "-C", source, "status", "--porcelain"]) == "", "Smoke dirtied release source")
    return {"status": "PASS", "tag": args.tag, "release_sha": args.sha, "release_tree": tree,
            "workflow_sha": os.environ["GITHUB_SHA"], "baseline_tag": args.baseline_tag,
            "approved_archive_sha256": args.checksum, "release_api": api,
            "checks": ["four real published aliases", "verified published baseline (manual managed layout)",
                       "clean published install", "real update --check leaves state unchanged",
                       "real default-latest update preserves baseline", "both installed CLIs doctor/validate/render"],
            "scope": "Real GitHub HTTPS endpoints, no loopback fixture. PDF smoke is not visual acceptance."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("tag", "sha", "checksum", "baseline-tag"):
        parser.add_argument("--" + flag, required=True)
    parser.add_argument("--out", type=Path, required=True, help="Fresh evidence directory under RUNNER_TEMP")
    args = parser.parse_args()
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted":
        raise SystemExit("Run published release acceptance only in a disposable GitHub-hosted VM.")
    require(all(re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag) for tag in (args.tag, args.baseline_tag)), "Invalid tag")
    require(tuple(map(int, args.baseline_tag[1:].split("."))) < tuple(map(int, args.tag[1:].split("."))), "Invalid baseline")
    require(re.fullmatch(r"[0-9a-f]{40}", args.sha) and re.fullmatch(r"[0-9a-f]{64}", args.checksum), "Invalid SHA/checksum")
    out = args.out.resolve()
    require(Path(os.environ["RUNNER_TEMP"]).resolve() in out.parents and ROOT not in out.parents,
            "Evidence must be outside checkout under RUNNER_TEMP")
    out.mkdir(parents=True, exist_ok=False)
    try:
        result = accept(args, out)
    except Exception as exc:
        (out / "result.json").write_text(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2) + "\n")
        raise
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
