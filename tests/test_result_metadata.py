from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from media_tools.transcribe.result_metadata import metadata_sidecar_path, read_result_metadata, write_result_metadata


class ResultMetadataTests(unittest.TestCase):
    def test_sidecar_path_appends_meta_suffix(self) -> None:
        self.assertEqual(metadata_sidecar_path("sample.md"), Path("sample.md.meta.json"))

    def test_write_and_read_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            transcript_path = Path(tmp_dir) / "result.md"
            transcript_path.write_text("# ok\n", encoding="utf-8")
            payload = {"record_id": "abc123", "remote_deleted": True}

            sidecar = write_result_metadata(transcript_path, payload)

            self.assertTrue(sidecar.exists())
            self.assertEqual(read_result_metadata(transcript_path), payload)
