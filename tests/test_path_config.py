import importlib
import os
import unittest
from unittest.mock import patch


class PathConfigTests(unittest.TestCase):
    TARGET_KEYS = (
        "OASIS_ROOT",
        "OASIS_SANCHUL_ROOT",
        "OASIS_CONFIG_DIR",
        "OASIS_DB_DIR",
        "OASIS_LOG_DIR",
    )

    def _reload_module(self, env_updates):
        clean_env = {k: v for k, v in os.environ.items() if k not in self.TARGET_KEYS}
        clean_env.update(env_updates)
        with patch.dict(os.environ, clean_env, clear=True):
            module = importlib.import_module("utils.path_config")
            return importlib.reload(module)

    def test_defaults_when_env_is_missing(self):
        module = self._reload_module({})
        self.assertEqual(module.SANCHUL_ROOT, module.REPO_ROOT)
        self.assertEqual(module.OASIS_ROOT, module.REPO_ROOT.parent)
        self.assertEqual(module.CONFIG_DIR, module.OASIS_ROOT / "config")
        self.assertEqual(module.DB_DIR, module.OASIS_ROOT / "db1")
        self.assertEqual(module.LOG_DIR, module.OASIS_ROOT / "logs")

    def test_env_overrides_all_paths(self):
        module = self._reload_module(
            {
                "OASIS_ROOT": r"Z:\oasis",
                "OASIS_SANCHUL_ROOT": r"Z:\oasis\SANCHUL_Sheet_1",
                "OASIS_CONFIG_DIR": r"Z:\oasis\config2",
                "OASIS_DB_DIR": r"Z:\oasis\db2",
                "OASIS_LOG_DIR": r"Z:\oasis\logs2",
            }
        )
        self.assertEqual(str(module.OASIS_ROOT), r"Z:\oasis")
        self.assertEqual(str(module.SANCHUL_ROOT), r"Z:\oasis\SANCHUL_Sheet_1")
        self.assertEqual(str(module.CONFIG_DIR), r"Z:\oasis\config2")
        self.assertEqual(str(module.DB_DIR), r"Z:\oasis\db2")
        self.assertEqual(str(module.LOG_DIR), r"Z:\oasis\logs2")

    def test_resolve_path_is_under_sanchul_root(self):
        module = self._reload_module({"OASIS_SANCHUL_ROOT": r"Z:\oasis\SANCHUL_Sheet_1"})
        resolved = module.resolve_path("data", "manual_mapping.json")
        self.assertEqual(
            resolved,
            r"Z:\oasis\SANCHUL_Sheet_1\data\manual_mapping.json",
        )


if __name__ == "__main__":
    unittest.main()
