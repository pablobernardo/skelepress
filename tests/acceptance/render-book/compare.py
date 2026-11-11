"""Compare public render/book behavior from two prepared toolkit archives.

Revision selection belongs to the caller, never this test. Requires the real
rendering toolchain; use only disposable hosted runners for actual PDF probes.
"""

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent


def validate(archive):
    """Validate both public inputs before executing either toolkit."""
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        size = 0
        for member in source.getmembers():
            path = PurePosixPath(member.name)
            if (path.is_absolute() or ".." in path.parts
                    or not (member.isfile() or member.isdir())
                    or any(part in (".git", ".ssh", "secrets")
                           or part.startswith(".env") for part in path.parts)):
                raise ValueError("unsafe archive member: " + member.name)
            size += member.size
        if size > 2 * 1024 ** 2:
            raise ValueError("public payload exceeds 2 MiB")


def materialize(archive, toolkit):
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        for member in source.getmembers():
            target = toolkit / member.name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                stream = source.extractfile(member)
                if stream is None:
                    raise ValueError("missing archive data: " + member.name)
                with stream:
                    target.write_bytes(stream.read())
                target.chmod(member.mode & 0o777)


def exercise(root, evidence, archives, records):
    project, toolkit = root / "project", root / "toolkit"
    env = {"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1",
           "LANG": "C", "LC_ALL": "C", "TZ": "UTC", "SKELEPRESS_LANG": "en"}
    environment = {"HOME": "home", "TMPDIR": "tmp", "XDG_CACHE_HOME": "cache",
                   "XDG_CONFIG_HOME": "config", "XDG_DATA_HOME": "data"}
    for variant, archive in archives.items():
        for path in (toolkit, project):
            if path.exists():
                shutil.rmtree(path)
        shutil.copytree(HERE / "fixture", project)
        shutil.copytree(project / "chapters", project / "work/chapters")
        materialize(archive, toolkit)
        for variable, directory in environment.items():
            path = root / directory
            if path.exists():
                shutil.rmtree(path)
            path.mkdir()
            env[variable] = str(path)
        records[variant] = {"archive_sha256": hashlib.sha256(archive).hexdigest(),
                            "commands": {}}
        commands = {
            "render": [str(toolkit / "bin/skelepress"), "render", "-c",
                       str(project / "skelepress.config.yaml")],
            "book": [str(toolkit / "bin/skelepress"), "book", "--out",
                     str(root / "book-out"), str(project)],
        }
        for command, argv in commands.items():
            output = evidence / variant / command
            output.mkdir(parents=True)
            try:
                result = subprocess.run(argv, cwd=project, env=env,
                                        capture_output=True, timeout=300)
                stdout, stderr, status = result.stdout, result.stderr, result.returncode
            except subprocess.TimeoutExpired as error:
                stdout, stderr, status = error.stdout or b"", error.stderr or b"", 124
            (output / "stdout").write_bytes(stdout)
            (output / "stderr").write_bytes(stderr)
            (output / "exit").write_text(str(status) + "\n")
            records[variant]["commands"][command] = {"argv": argv, "exit": status}
            generated = project / "work/out" if command == "render" else root / "book-out"
            if generated.exists():
                shutil.move(generated, output / "generated")
            if status:
                raise ValueError(variant + " " + command + " failed; see retained streams")


def compare(evidence, records):
    checks = {}
    for command, extension in (("render", ".epub"), ("book", ".pdf")):
        for stream in ("stdout", "stderr", "exit"):
            checks[command + "." + stream] = (
                (evidence / "base" / command / stream).read_bytes()
                == (evidence / "candidate" / command / stream).read_bytes())
        for variant in ("base", "candidate"):
            files = list((evidence / variant / command / "generated").rglob("*" + extension))
            checks[variant + "." + command + ".artifact"] = (
                len(files) == 1 and files[0].stat().st_size > 0)
    records["checks"] = checks
    for name, passed in checks.items():
        print(("PASS " if passed else "FAIL ") + name)
    return 0 if all(checks.values()) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_archive", type=Path)
    parser.add_argument("candidate_archive", type=Path)
    parser.add_argument("--evidence", required=True, type=Path,
                        help="New caller-owned directory for raw streams, artifacts and result.json")
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    records = {}
    if evidence.exists():
        print("ERROR: evidence directory already exists", file=sys.stderr)
        return 1
    try:
        # Check before allocating scratch or unpacking either toolkit.
        for path in (evidence.parent, Path(tempfile.gettempdir())):
            if shutil.disk_usage(path).free < 1024 ** 3:
                raise ValueError("less than 1 GiB scratch capacity")
        evidence.mkdir()
        archives = {}
        for variant, path in (("base", args.base_archive), ("candidate", args.candidate_archive)):
            if path.stat().st_size > 4 * 1024 ** 2:
                raise ValueError("public archive exceeds 4 MiB")
            # Freeze exactly the bytes validated, hashed and later unpacked.
            archives[variant] = path.read_bytes()
            validate(archives[variant])
        with tempfile.TemporaryDirectory(prefix="skelepress-cli-") as scratch:
            exercise(Path(scratch).resolve(), evidence, archives, records)
        status = compare(evidence, records)
    except (OSError, ValueError, tarfile.TarError) as error:
        records["error"] = str(error)
        print("ERROR: " + str(error), file=sys.stderr)
        status = 1
    finally:
        if evidence.is_dir():
            (evidence / "result.json").write_text(json.dumps(records, indent=2) + "\n")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
