"""Fail on suspected secrets in tracked and non-ignored new files, without printing values."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    paths = (
        subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        )
        .stdout.decode("utf-8")
        .split("\0")
    )
    files = sorted({path for path in paths if path and (ROOT / path).is_file()})
    findings = 0
    # Bound command length on Windows as the repository grows.
    for offset in range(0, len(files), 40):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "detect_secrets",
                "-c",
                "1",
                "scan",
                "--no-verify",
                "--all-files",
                *files[offset : offset + 40],
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        for filename, secrets in json.loads(result.stdout)["results"].items():
            for secret in secrets:
                print(f"{filename}:{secret['line_number']}: {secret['type']} (value redacted)")
                findings += 1
    print(f"Secret scan: {len(files)} files, {findings} potential secrets.")
    return 1 if findings else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError, ValueError, OSError:
        print(
            "Secret scanning failed; check Git and the locked scanner installation.",
            file=sys.stderr,
        )
        sys.exit(2)
