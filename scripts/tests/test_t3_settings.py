"""Configuration-only persistence must never snapshot projects or runtimes."""
import importlib.util
import pathlib
import tempfile
import unittest

HELPER = pathlib.Path(__file__).resolve().parents[2] / "kubernetes/coder/workspace-templates/t3code/settings-sync.py"


class SettingsTests(unittest.TestCase):
    def test_only_allowlisted_configuration_is_copied(self):
        self.assertTrue(HELPER.is_file(), "configuration-only persistence helper is missing")
        spec = importlib.util.spec_from_file_location("settings_sync", HELPER)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            home, persist = root / "home", root / "persist"
            files = {
                ".codex/config.toml": "model='test'",
                ".codex/auth.json": '{"test_fixture":true}',
                ".t3/userdata/settings.json": "{}",
                ".config/opencode/opencode.json": "{}",
                ".codex/state_5.sqlite": "not-a-real-database",
                ".t3/userdata/statev2.sqlite": "not-a-real-database",
                ".config/opencode/node_modules/dependency/index.js": "dependency",
                ".t3/runtime/bin/t3": "runtime",
                "projects/demo/main.py": "project",
            }
            for name, content in files.items():
                path = home / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            module.sync_configs(home, persist)
            copied = {str(p.relative_to(persist)) for p in persist.rglob("*") if p.is_file()}
            self.assertEqual(copied, {".codex/config.toml", ".codex/auth.json", ".t3/userdata/settings.json", ".config/opencode/opencode.json"})
            # Model an application's atomic replacement, not an in-place write.
            replacement = home / ".codex/config.new"
            replacement.write_text("model='changed'")
            replacement.replace(home / ".codex/config.toml")
            module.sync_configs(home, persist)
            self.assertEqual((persist / ".codex/config.toml").read_text(), "model='changed'")
            # Logout/removal must not resurrect an old credential at next boot.
            (home / ".codex/auth.json").unlink()
            module.sync_configs(home, persist)
            self.assertFalse((persist / ".codex/auth.json").exists())
            restored = root / "fresh-home"
            module.sync_configs(persist, restored)
            self.assertEqual((restored / ".codex/config.toml").read_text(), "model='changed'")
            self.assertFalse((restored / "projects").exists())


if __name__ == "__main__":
    unittest.main()
