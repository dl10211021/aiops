import subprocess
import sys


def _github_escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> int:
    command = [
        sys.executable,
        "-W",
        "default",
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-p",
        "test*.py",
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output = completed.stdout
    print(output, end="")

    if completed.returncode:
        lines = output.splitlines()[-80:]
        details = _github_escape("\n".join(lines))
        print(f"::error title=Backend unit tests failed::{details}")

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
