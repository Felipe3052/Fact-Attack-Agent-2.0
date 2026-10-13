"""hf_dataset._download: retries a broken transfer, accepts only complete PDFs."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import hf_dataset


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def read(self):
        if isinstance(self.data, Exception):
            raise self.data
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TestDownload(unittest.TestCase):
    def run_download(self, answers):
        calls = iter(answers)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(hf_dataset.urllib.request, "urlopen", lambda req, timeout: FakeResponse(next(calls))), \
                mock.patch.object(hf_dataset.time, "sleep", lambda s: None):
            dest = Path(tmp) / "booklet.pdf"
            ok = hf_dataset._download("https://example.org/b.pdf", dest)
            return ok, (dest.read_bytes() if dest.exists() else None), list(Path(tmp).iterdir())

    def test_interrupted_read_is_retried(self):
        ok, data, files = self.run_download([ConnectionError("IncompleteRead"), b"%PDF-1.7 complete"])
        self.assertTrue(ok)
        self.assertEqual(data, b"%PDF-1.7 complete")
        self.assertEqual([f.name for f in files], ["booklet.pdf"])  # no .part file left

    def test_non_pdf_is_rejected_and_retried(self):
        ok, data, _ = self.run_download([b"<html>error</html>", b"%PDF-1.4 ok"])
        self.assertTrue(ok)
        self.assertEqual(data, b"%PDF-1.4 ok")

    def test_gives_up_after_all_attempts(self):
        ok, data, files = self.run_download([ConnectionError("x")] * hf_dataset.DOWNLOAD_ATTEMPTS)
        self.assertFalse(ok)
        self.assertIsNone(data)
        self.assertEqual(files, [])


if __name__ == "__main__":
    unittest.main()
