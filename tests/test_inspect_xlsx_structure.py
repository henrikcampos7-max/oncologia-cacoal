import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "inspect_xlsx_structure.py"


class InspectXlsxStructureCliTests(unittest.TestCase):
    def test_returns_validation_error_when_missing_arguments(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
        self.assertIn("usage:", payload["error"]["message"])

    def test_returns_internal_error_for_invalid_xlsx_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "fake.xlsx"
            output_path = temp_path / "out.json"
            input_path.write_text("not-a-zip-xlsx", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(input_path), str(output_path)],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stderr.splitlines()[-1])
        self.assertEqual(payload["error"]["code"], "INTERNAL_ERROR")


if __name__ == "__main__":
    unittest.main()
