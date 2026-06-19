from __future__ import annotations

from pathlib import Path

from authorized_web_exporter.models import CrawlError, DataRecord
from authorized_web_exporter.storage import export_records


def test_export_records_creates_expected_files(tmp_path: Path) -> None:
    records = [
        DataRecord(
            source_url="https://example.com/detail/1",
            record_id="1",
            title="サンプル物件",
            fields={"price": "1000万円"},
            key_values={"所在地": "東京都"},
            images=["https://example.com/a.jpg"],
            links=["https://example.com/detail"],
            raw_text="サンプル本文",
        )
    ]
    errors = [CrawlError(url="https://example.com/error", phase="detail", message="timeout")]

    export_records(tmp_path, records, errors)

    assert (tmp_path / "records.csv").exists()
    assert (tmp_path / "records.xlsx").exists()
    assert (tmp_path / "records.jsonl").exists()
    assert (tmp_path / "records.txt").exists()
    assert (tmp_path / "errors.jsonl").exists()
    assert "サンプル物件" in (tmp_path / "records.txt").read_text(encoding="utf-8")
