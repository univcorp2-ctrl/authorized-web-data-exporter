from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from authorized_web_exporter.models import CrawlError, DataRecord


class CheckpointStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.visited_list_pages: set[str] = set()
        self.visited_detail_urls: set[str] = set()
        self.records_by_url: dict[str, DataRecord] = {}
        self.errors: list[CrawlError] = []

    def load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.visited_list_pages = set(data.get("visited_list_pages") or [])
        self.visited_detail_urls = set(data.get("visited_detail_urls") or [])
        self.records_by_url = {
            item["source_url"]: DataRecord.from_dict(item)
            for item in data.get("records", [])
            if item.get("source_url")
        }
        self.errors = [CrawlError.from_dict(item) for item in data.get("errors", [])]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "visited_list_pages": sorted(self.visited_list_pages),
            "visited_detail_urls": sorted(self.visited_detail_urls),
            "records": [record.to_dict() for record in self.records_by_url.values()],
            "errors": [error.to_dict() for error in self.errors],
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_list_page(self, url: str) -> None:
        self.visited_list_pages.add(url)
        self.save()

    def add_record(self, record: DataRecord) -> None:
        self.visited_detail_urls.add(record.source_url)
        self.records_by_url[record.source_url] = record
        self.save()

    def add_error(self, error: CrawlError) -> None:
        self.errors.append(error)
        self.save()

    @property
    def records(self) -> list[DataRecord]:
        return list(self.records_by_url.values())
