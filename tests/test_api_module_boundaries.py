import unittest
from pathlib import Path


class TestApiModuleBoundaries(unittest.TestCase):
    def test_runtime_api_code_uses_domain_schema_modules(self):
        api_root = Path(__file__).resolve().parents[1] / "api"
        allowed = {
            api_root / "schemas.py",
            api_root / "request_models.py",
        }

        offenders = []
        for path in api_root.rglob("*.py"):
            if path in allowed:
                continue
            content = path.read_text(encoding="utf-8")
            if "from api.schemas import" in content or "import api.schemas" in content:
                offenders.append(path.relative_to(api_root.parent).as_posix())

        self.assertEqual(offenders, [])

    def test_runtime_api_code_uses_domain_response_mappers(self):
        api_root = Path(__file__).resolve().parents[1] / "api"
        allowed = {api_root / "mappers.py"}

        offenders = []
        for path in api_root.rglob("*.py"):
            if path in allowed:
                continue
            content = path.read_text(encoding="utf-8")
            if "from api.mappers import" in content or "import api.mappers" in content:
                offenders.append(path.relative_to(api_root.parent).as_posix())

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
