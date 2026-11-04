import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import setup_model


class ModelSetupTests(unittest.TestCase):
    def test_download_verify_and_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "models/gradient").mkdir(parents=True)
            data = b"test artifact"
            metadata = dict(
                size=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                source=setup_model.PREFIX + "test",
            )
            (root / "models/gradient/manifest.json").write_text(
                json.dumps({"files": {name: metadata for name in setup_model.FILES}})
            )
            destination = root / "downloaded"
            with (
                patch.object(setup_model, "ROOT", root),
                patch("sys.argv", ["setup_model.py", "--model-dir", str(destination)]),
                patch.object(
                    setup_model.urllib.request,
                    "urlopen",
                    side_effect=lambda *a, **k: io.BytesIO(data),
                ) as network,
            ):
                setup_model.main()
                self.assertEqual(network.call_count, 3)
                setup_model.main()
                self.assertEqual(network.call_count, 3)
                (destination / "config.json").write_bytes(b"bad")
                with (
                    patch(
                        "sys.argv",
                        ["setup_model.py", "--check", "--model-dir", str(destination)],
                    ),
                    self.assertRaises(SystemExit),
                ):
                    setup_model.main()
                self.assertEqual(network.call_count, 3)

    def test_corrupt_download_does_not_replace_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "models/gradient").mkdir(parents=True)
            metadata = dict(
                size=5,
                sha256=hashlib.sha256(b"valid").hexdigest(),
                source=setup_model.PREFIX + "test",
            )
            (root / "models/gradient/manifest.json").write_text(
                json.dumps({"files": {name: metadata for name in setup_model.FILES}})
            )
            destination = root / "downloaded"
            destination.mkdir(parents=True)
            (destination / "model.onnx").write_bytes(b"old")
            with (
                patch.object(setup_model, "ROOT", root),
                patch("sys.argv", ["setup_model.py", "--model-dir", str(destination)]),
                patch.object(
                    setup_model.urllib.request,
                    "urlopen",
                    return_value=io.BytesIO(b"wrong"),
                ),
            ):
                with self.assertRaisesRegex(ValueError, "integrity"):
                    setup_model.main()
            self.assertEqual((destination / "model.onnx").read_bytes(), b"old")
            self.assertFalse((destination / "model.onnx.part").exists())


if __name__ == "__main__":
    unittest.main()
