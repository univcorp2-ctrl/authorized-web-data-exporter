from __future__ import annotations

from authorized_web_exporter.config import DiscoverySettings, ExtractionSettings, FieldRule
from authorized_web_exporter.parser import extract_detail_links, extract_next_links, parse_detail_page


def test_parse_detail_page_extracts_fields_from_table_and_selectors() -> None:
    html = """
    <html><head><title>Fallback Title</title></head>
    <body>
      <h1>新宿区サンプルマンション</h1>
      <table>
        <tr><th>価格</th><td>1,980万円</td></tr>
        <tr><th>表面利回り</th><td>6.5%</td></tr>
        <tr><th>所在地</th><td>東京都新宿区西新宿1丁目</td></tr>
      </table>
      <div class="custom-code">CODE-12345</div>
      <img src="/images/sample.jpg" />
      <a href="/contact">問い合わせ</a>
    </body></html>
    """
    extraction = ExtractionSettings(
        fields=[
            FieldRule(name="price", labels=["価格"]),
            FieldRule(name="yield", labels=["利回り"]),
            FieldRule(name="code", selectors=[".custom-code"], regex=r"CODE-(\d+)"),
        ]
    )

    record = parse_detail_page(html, "https://www.kenbiya.com/app/exe/property/12345", extraction)

    assert record.record_id == "12345"
    assert record.title == "新宿区サンプルマンション"
    assert record.fields["price"] == "1,980万円"
    assert record.fields["yield"] == "6.5%"
    assert record.fields["code"] == "12345"
    assert "https://www.kenbiya.com/images/sample.jpg" in record.images


def test_extract_detail_and_next_links() -> None:
    html = """
    <html><body>
      <a href="/app/exe/property/100">物件A</a>
      <a href="https://www.kenbiya.com/app/exe/detail/200">物件B</a>
      <a rel="next" href="/app/exe/search?page=2">次へ</a>
    </body></html>
    """
    discovery = DiscoverySettings(
        detail_link_selectors=["a[href*='property']"],
        detail_url_regexes=[r"/detail/\d+"],
        next_page_selectors=["a[rel='next']"],
        next_texts=["次へ"],
    )

    links = extract_detail_links(
        html,
        "https://www.kenbiya.com/app/exe/search?page=1",
        discovery,
        ["www.kenbiya.com"],
    )
    next_links = extract_next_links(
        html,
        "https://www.kenbiya.com/app/exe/search?page=1",
        discovery,
        ["www.kenbiya.com"],
    )

    assert links == [
        "https://www.kenbiya.com/app/exe/property/100",
        "https://www.kenbiya.com/app/exe/detail/200",
    ]
    assert next_links == ["https://www.kenbiya.com/app/exe/search?page=2"]
