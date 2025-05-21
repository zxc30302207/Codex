from scraper import Parser


def test_parse_title_and_links():
    html = """<html><head><title>Hello</title></head>\
                 <body><a href='/a'>A</a><a href='https://b.com'>B</a></body></html>"""
    p = Parser()
    result = p.parse(html, "https://example.com")
    assert result["title"] == "Hello"
    assert "https://example.com/a" in result["links"]
