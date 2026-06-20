from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> None:
    groovy = shutil.which("groovy")
    if groovy is None:
        print("groovy not installed; install Groovy to run CalculatorTest.groovy")
        return
    subprocess.run([groovy, str(ROOT / "CalculatorTest.groovy")], check=True)


if __name__ == "__main__":
    main()

