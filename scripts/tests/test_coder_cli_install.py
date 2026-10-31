"""Only a checksum-verified Coder executable may replace the installed CLI."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "install-coder-cli.py"


class InstallerTests(unittest.TestCase):
    def test_checksum_failure_preserves_existing_binary(self):
        self.assertTrue(SOURCE.is_file())
        spec = importlib.util.spec_from_file_location("cli_install", SOURCE)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "coder_test.tar.gz"
            data = b"synthetic CLI test fixture, not a downloaded binary"
            with tarfile.open(archive, "w:gz") as tar:
                entry = tarfile.TarInfo("./coder")
                entry.size = len(data)
                tar.addfile(entry, io.BytesIO(data))
            target = root / "bin/coder"
            target.parent.mkdir()
            target.write_bytes(b"existing test fixture")
            sums = root / "checksums.txt"
            sums.write_text("0" * 64 + "  " + archive.name + "\n")
            with self.assertRaises(ValueError):
                module.install_verified(archive, sums, target)
            self.assertEqual(target.read_bytes(), b"existing test fixture")
            sums.write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n")
            module.install_verified(archive, sums, target)
            self.assertEqual(target.read_bytes(), data)
            self.assertEqual(target.stat().st_mode & 0o777, 0o755)


if __name__ == "__main__":
    unittest.main()
