from __future__ import annotations

from pathlib import Path

from authorized_web_exporter.dashboard import build_dashboard_html, write_dashboard


def test_build_dashboard_html_contains_filters_and_data() -> None:
    html = build_dashboard_html(
        [
            {
                "仕入れ判定": "A",
                "物件名": "サンプル物件",
                "価格（万円）": 5000,
                "DSCR": 1.4,
                "詳細URL": "https://example.com/detail/1",
                "_secret_internal": "hidden",
            }
        ],
        {"対象件数": 1, "APIキー取得元": "env:REINFOLIB_API_KEY"},
    )
    assert "投資分析ダッシュボード" in html
    assert "サンプル物件" in html
    assert "_secret_internal" not in html
    assert "APIキー取得元" not in html
    assert "id=\"search\"" in html


def test_write_dashboard_creates_index_html(tmp_path: Path) -> None:
    path = write_dashboard(tmp_path, [{"仕入れ判定": "B", "物件名": "物件B"}], {"対象件数": 1})
    assert path == tmp_path / "index.html"
    assert path.exists()
    assert "物件B" in path.read_text(encoding="utf-8")
