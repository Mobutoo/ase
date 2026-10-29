"""Resolve runtime pins for the current Python/platform using pip's report."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory() as tmp:
    report = Path(tmp) / "resolved.json"
    subprocess.run([sys.executable, "-m", "pip", "install", "--dry-run",
                    "--ignore-installed", "--report", str(report),
                    "-r", str(root / "requirements.txt")], check=True)
    pins = []
    for item in json.loads(report.read_text())["install"]:
        metadata = item["metadata"]
        name = metadata["name"]
        if name.lower() == "uvicorn":
            name += "[standard]"
        pins.append(f"{name}=={metadata['version']}")
    (root / "requirements.lock").write_text(
        "# Resolved for Python 3.12 / Linux. Runtime dependencies only.\n"
        "# Regenerate after editing requirements.txt; see docs/MAINTENANCE.md.\n"
        + "\n".join(sorted(pins, key=str.lower)) + "\n"
    )
