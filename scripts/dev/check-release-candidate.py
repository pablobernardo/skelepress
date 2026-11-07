#!/usr/bin/env python3
"""Accept committed candidate artifacts in a disposable hosted CI VM, without publishing."""
from __future__ import annotations

import argparse
import functools
import hashlib
import http.client
import http.server
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
from pathlib import Path, PurePosixPath
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[2]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url):
    for _ in range(6):
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        require(parsed.scheme == "https" and not parsed.username and not parsed.password
                and parsed.port in (None, 443) and (host in ("api.github.com", "github.com")
                or host.endswith(".githubusercontent.com")), "Release download escaped permitted HTTPS hosts")
        connection = http.client.HTTPSConnection(host, timeout=120)
        try:
            connection.request("GET", parsed.path + ("?" + parsed.query if parsed.query else ""),
                               headers={"User-Agent": "skelepress-candidate-acceptance"})
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                require(bool(location), "Release redirect has no location")
                url = urljoin(url, location)
                continue
            require(response.status == 200, f"Release download failed: HTTP {response.status}")
            return response.read()
        finally:
            connection.close()
    raise RuntimeError("Too many release download redirects")


def parse_json(raw):
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError("Invalid published release JSON") from exc


def accept(out):
    commands = []

    def run(args, env=None, expected=0, budget=180):
        try:
            result = subprocess.run([str(a) for a in args], cwd=ROOT, env=env,
                                    text=True, capture_output=True, timeout=budget)
        except subprocess.TimeoutExpired as exc:
            def decoded(value):
                return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
            result = subprocess.CompletedProcess(args, 124, decoded(exc.stdout), decoded(exc.stderr))
        index = len(commands)
        (out / f"{index:02d}.stdout").write_text(result.stdout)
        (out / f"{index:02d}.stderr").write_text(result.stderr)
        commands.append({"args": [str(a) for a in args], "exit_code": result.returncode,
                         "stdout": f"{index:02d}.stdout", "stderr": f"{index:02d}.stderr"})
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        require(result.returncode == expected, f"Unexpected exit {result.returncode}; see command {index}")
        return result.stdout

    require(run(["git", "status", "--porcelain"]) == "", "Candidate checkout must be clean")
    head = run(["git", "rev-parse", "HEAD"]).strip()
    require(head == os.environ["GITHUB_SHA"], "Candidate differs from dispatched SHA")
    version = (ROOT / "VERSION").read_text().strip()
    latest = parse_json(fetch(f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/releases/latest"))
    previous = latest["tag_name"]
    require(tuple(map(int, version.split("."))) > tuple(map(int, previous.lstrip("v").split("."))),
            "Candidate must be newer than the published stable release")
    (out / "previous-release.json").write_text(json.dumps(latest, indent=2) + "\n")
    artifacts = out / "artifacts"
    run(["bash", ROOT / "scripts/delivery/package-release.sh", artifacts])
    with tempfile.TemporaryDirectory(prefix="skelepress-acceptance-", dir=os.environ["RUNNER_TEMP"]) as temporary:
        work = Path(temporary)
        run(["bash", ROOT / "scripts/delivery/package-release.sh", work / "second-build"])
        checksums = dict(line.split()[::-1] for line in (artifacts / "checksums.txt").read_text().splitlines())
        expected_names = {f"skelepress_{system}_{arch}.tar.gz" for system in ("darwin", "linux") for arch in ("amd64", "arm64")}
        require(set(checksums) == expected_names, "Unexpected platform artifacts")
        for name, checksum in checksums.items():
            require(digest(artifacts / name) == checksum == digest(work / "second-build" / name), "Non-reproducible archive or checksum mismatch")
            with tarfile.open(artifacts / name) as archive:
                members = archive.getmembers()
                names = {m.name for m in members}
                require(all(not PurePosixPath(m.name).is_absolute() and ".." not in PurePosixPath(m.name).parts for m in members), "Unsafe archive path")
                require(not any("__pycache__" in n or n.endswith(".pyc") for n in names), "Bytecode in payload")
                require({"bin/skelepress", "VERSION", "LICENSE", "schemas/skelepress-config.schema.json",
                         "templates/default.tex", "templates/book.tex", "i18n/locales/en.json",
                         "i18n/locales/es.json", "i18n/locales/gl.json", "i18n/locales/pt.json",
                         "scripts/runtime/render-native.py"} <= names, "Incomplete payload")
                require(archive.getmember("bin/skelepress").mode & 0o111, "CLI is not executable")
                version_file = archive.extractfile("VERSION")
                if version_file is None:
                    raise RuntimeError("Packaged VERSION is not a regular file")
                with version_file:
                    require(version_file.read().decode().strip() == version, "Wrong packaged version")
        require(len(set(checksums.values())) == 1, "Platform aliases must share one payload")
        system = "darwin" if platform.system() == "Darwin" else "linux"
        arch = "arm64" if platform.machine() in ("aarch64", "arm64") else "amd64"
        name = f"skelepress_{system}_{arch}.tar.gz"
        serve = work / "http"
        (serve / "releases/tags").mkdir(parents=True)
        for folder in ("previous", "candidate", "invalid-version", "invalid-checksum"):
            (serve / folder).mkdir()
        for asset in latest["assets"]:
            if asset["name"] in (name, "checksums.txt"):
                (serve / "previous" / asset["name"]).write_bytes(fetch(asset["browser_download_url"]))
        old_sums = dict(line.split()[::-1] for line in (serve / "previous/checksums.txt").read_text().splitlines())
        require(digest(serve / "previous" / name) == old_sums[name], "Published baseline checksum failed")
        for filename in (name, "checksums.txt"):
            shutil.copyfile(artifacts / filename, serve / "candidate" / filename)
        with tarfile.open(artifacts / name) as source, tarfile.open(serve / "invalid-version" / name, "w:gz") as target:
            for member in source.getmembers():
                data = b"0.0.0\n" if member.name == "VERSION" else None
                if data is not None:
                    member.size = len(data)
                target.addfile(member, io.BytesIO(data) if data is not None else source.extractfile(member) if member.isfile() else None)
        (serve / "invalid-version/checksums.txt").write_text(f"{digest(serve / 'invalid-version' / name)}  {name}\n")
        shutil.copyfile(artifacts / name, serve / "invalid-checksum" / name)
        (serve / "invalid-checksum/checksums.txt").write_text(f"{'0' * 64}  {name}\n")
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(serve))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"

        def release(tag, folder):
            data = {"tag_name": tag, "assets": [{"name": filename, "browser_download_url": f"{base}/{folder}/{filename}"}
                    for filename in (name, "checksums.txt")]}
            (serve / "releases/latest").write_text(json.dumps(data))
            (serve / "releases/tags" / tag).write_text(json.dumps(data))

        def environment(label):
            env = os.environ.copy()
            home = work / label
            env.update(HOME=str(home), SKELEPRESS_INSTALL_HOME=str(home / "managed"),
                       SKELEPRESS_INSTALL_DIR=str(home / "bin"), SKELEPRESS_RELEASE_API_BASE=base + "/releases",
                       SKELEPRESS_UPDATE_API_BASE=base + "/releases", SKELEPRESS_UPDATE_LOG_FILE=str(out / (label + ".log")))
            return env, home / "bin/skelepress", home / "managed/current"

        def installed_version(cli, env, expected):
            require(run([cli, "--version"], env) == f"skelepress {expected}\n", "Wrong installed public version")

        try:
            clean_env, clean_cli, clean_current = environment("clean")
            release("v" + version, "candidate")
            run(["bash", ROOT / "scripts/delivery/install.sh"], clean_env)
            installed_version(clean_cli, clean_env, version)
            require(clean_current.resolve().name == "v" + version, "Wrong clean-install current pointer")
            upgrade_env, upgrade_cli, current = environment("upgrade")
            release(previous, "previous")
            run(["bash", ROOT / "scripts/delivery/install.sh"], upgrade_env)
            installed_version(upgrade_cli, upgrade_env, previous.lstrip("v"))
            old_current, old_binary = os.readlink(current), os.readlink(upgrade_cli)
            old_files = {str(p.relative_to(current.resolve())): digest(p) for p in current.resolve().rglob("*") if p.is_file()}
            for tag, folder in (("v98.0.0", "invalid-checksum"), ("v99.0.0", "invalid-version")):
                release(tag, folder)
                run([upgrade_cli, "update", "--to", tag, "--yes"], upgrade_env, expected=1)
                require(os.readlink(current) == old_current and os.readlink(upgrade_cli) == old_binary, "Failure changed public managed pointers")
                require(old_files == {str(p.relative_to(current.resolve())): digest(p) for p in current.resolve().rglob("*") if p.is_file()}, "Failure changed previous installed payload")
                installed_version(upgrade_cli, upgrade_env, previous.lstrip("v"))
            require("post-install version validation failed" in (out / "upgrade.log").read_text(), "Rollback did not reach post-install validation")
            release("v" + version, "candidate")
            run([upgrade_cli, "update", "--to", version, "--yes"], upgrade_env)
            installed_version(upgrade_cli, upgrade_env, version)
            require(current.resolve().name == "v" + version, "Upgrade did not switch current")
            (work / "chapters").mkdir()
            (work / "chapters/review.md").write_text("# Candidate chapter\n\nInline `code` and a paragraph.\n\n## Highlighted code\n\n```python\nprint('candidate')\n```\n\n```\nuntagged code\n```\n\nSymbols: ☐ ☑ ☒ ✅ ❌ ⚠\n\nUnsupported character: 漢\n\n" + "A representative paragraph for pagination. " * 140)
            config = {"version": 1, "project": {"name": "candidate-review", "base_dir": str(work)},
                      "document": {"title": "Candidate acceptance", "language": "en", "titlepage": False},
                      "input": {"chapters_dir": "chapters", "glob": "*.md", "order": "natural", "explicit_files": ["review.md"]},
                      "output": {"dir": "pdf", "file_prefix": "candidate", "suffix": "review", "keep_merged_markdown": True},
                      "pandoc": {"pdf_engine": "xelatex", "toc": False, "toc_depth": 3, "number_sections": True, "resource_path": ["."], "running_headers": True},
                      "filters": {"emoji": {"enabled": False}, "mermaid": {"enabled": False}, "extra_lua_filters": []},
                      "runtime": {"required_commands": ["pandoc", "xelatex"], "strict": True},
                      "compat": {"legacy_clearpage_between_h1": False}}
            config_path = work / "config.json"
            config_path.write_text(json.dumps(config))
            run(["pandoc", "--version"])
            run(["xelatex", "--version"])
            run(["fc-match", "FreeSerif"])
            run([clean_cli, "info", "--json"], clean_env)
            run([clean_cli, "validate-config", "-c", config_path], clean_env)
            run([clean_cli, "doctor", "-c", config_path], clean_env)
            run([clean_cli, "render", "-c", config_path], clean_env)
            require(any("Missing character" in (out / item["stderr"]).read_text() for item in commands), "Unsupported-character warning was not retained")
            shutil.copytree(work / "pdf", out / "pdfs")
            for fixture in ("enabled-filters-project", "l3-mermaid-project"):
                run([clean_cli, "render", "-c", ROOT / "tests/integration" / fixture / "skelepress.config.yaml"], clean_env)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    run([sys.executable, ROOT / "tests/integration/check-heading-pagination.py"])
    shutil.copyfile(ROOT / "examples/.output/heading-review/heading-pagination-review.pdf",
                    out / "pdfs/heading-pagination-review.pdf")
    for fixture in ("enabled-filters-project", "l3-mermaid-project"):
        for pdf in (ROOT / "tests/integration" / fixture / "output").glob("*.pdf"):
            shutil.copyfile(pdf, out / "pdfs" / (fixture + "-" + pdf.name))
    for pdf in (out / "pdfs").glob("*.pdf"):
        run(["pdftoppm", "-scale-to", "1400", "-png", pdf, pdf.with_suffix("")])
    require(run(["git", "status", "--porcelain"]) == "", "Acceptance dirtied candidate checkout")
    return {"status": "PASS", "head": head, "version": version, "previous_tag": previous,
            "tree": run(["git", "rev-parse", "HEAD^{tree}"]).strip(), "checksums": checksums,
            "checks": ["four package aliases", "two-build reproducibility", "clean install", "published-baseline checksum",
                       "checksum rejection", "post-version rollback", "previous-payload preservation", "published-stable-to-candidate upgrade",
                       "installed CLI doctor/validation/render", "public PDF/PNG evidence"],
            "scope": "Actual archives; local HTTP release API fixture. Real release downloads after publication remain deferred.",
            "visual_acceptance": "PENDING human/independent inspection; generated files alone are not acceptance"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Fresh evidence directory outside the Git checkout")
    args = parser.parse_args()
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted":
        raise SystemExit("Run release acceptance only in a disposable GitHub-hosted VM.")
    out = args.out.resolve()
    require(out != ROOT and ROOT not in out.parents, "Evidence must be outside the checkout")
    out.mkdir(parents=True, exist_ok=False)
    try:
        result = accept(out)
    except Exception as exc:
        (out / "result.json").write_text(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2) + "\n")
        raise
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
