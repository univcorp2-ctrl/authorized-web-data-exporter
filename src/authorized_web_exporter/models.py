from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class DataRecord:
    source_url: str
    fetched_at: str = field(default_factory=utc_now_iso)
    record_id: str | None = None
    title: str | None = None
    fields: dict[str, str] = field(default_factory=dict)
    key_values: dict[str, str] = field(default_factory=dict)
    images: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    raw_text: str | None = None
    html_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DataRecord":
        return cls(
            source_url=data["source_url"],
            fetched_at=data.get("fetched_at") or utc_now_iso(),
            record_id=data.get("record_id"),
            title=data.get("title"),
            fields=dict(data.get("fields") or {}),
            key_values=dict(data.get("key_values") or {}),
            images=list(data.get("images") or []),
            links=list(data.get("links") or []),
            raw_text=data.get("raw_text"),
            html_file=data.get("html_file"),
        )


@dataclass(slots=True)
class CrawlError:
    url: str
    message: str
    phase: str
    occurred_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CrawlError":
        return cls(
            url=data["url"],
            message=data.get("message", ""),
            phase=data.get("phase", "unknown"),
            occurred_at=data.get("occurred_at") or utc_now_iso(),
        )
