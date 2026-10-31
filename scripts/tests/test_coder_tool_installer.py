"""Exercise tool installer failures without downloading or installing software."""
import os
import pathlib
import subprocess
import tempfile
import unittest

INSTALLER = pathlib.Path(__file__).resolve().parents[2] / "kubernetes/coder/workspace-templates/t3code/install-tools.sh"


class InstallerTests(unittest.TestCase):
    def test_download_failure_never_runs_partial_installer(self):
        self.assertTrue(INSTALLER.is_file(), "bounded installer helper is missing")
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            fakebin = root / "bin"
            fakebin.mkdir()
            curl = fakebin / "curl"
            curl.write_text('#!/bin/sh\nwhile [ "$#" -gt 0 ]; do\n if [ "$1" = --output ]; then shift; printf \'touch "$HOME/executed"\\n\' > "$1"; fi\n shift\ndone\nexit 22\n')
            curl.chmod(0o755)
            env = dict(os.environ, HOME=str(root), TMPDIR=str(root), PATH=str(fakebin) + ":/usr/bin:/bin")
            result = subprocess.run(["bash", str(INSTALLER), "--update", "codex"], env=env, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("command not found", result.stderr)
            self.assertFalse((root / "executed").exists())
            self.assertFalse(list(root.glob("coder-install-*")))

    def test_existing_tool_skips_network_during_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            fakebin = root / "bin"
            fakebin.mkdir()
            for name, script in {
                "codex": '#!/bin/sh\nprintf "codex test-version\\n"\n',
                "curl": '#!/bin/sh\ntouch "$HOME/network-used"\nexit 99\n',
            }.items():
                executable = fakebin / name
                executable.write_text(script)
                executable.chmod(0o755)
            env = dict(os.environ, HOME=str(root), TMPDIR=str(root), PATH=str(fakebin) + ":/usr/bin:/bin")
            result = subprocess.run(["bash", str(INSTALLER), "codex"], env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / "network-used").exists())


if __name__ == "__main__":
    unittest.main()
