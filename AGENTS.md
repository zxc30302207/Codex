# AGENTS.md

## 專案簡介

**MiniSpider** 是一個「麻雀雖小、五臟俱全」的教學用多代理（Agent）爬蟲範例，專為初學者設計，示範如何以乾淨、可維護的方式組織一隻可擴充的網路爬蟲。文件以繁體中文撰寫，方便臺灣讀者閱讀。此檔案同時充當 Codex 的提示 (prompt) 與專案文件，讓 Codex 能快速理解整個專案結構與各 Agent 的職責，並生成或修改程式碼。

---

## 目標

1. **教學導向**：程式碼具備詳細註解與日誌，方便學習除錯流程。
2. **模組化**：以多 Agent 思維拆分責任，例如：`Fetcher`、`Parser`、`Saver`。
3. **可擴充**：加入新網站或新資料格式時，只需最小變動即可完成。
4. **守規則**：內建 robots.txt 檢查、隨機延遲與 User-Agent，示範友善抓取。

---

## 專案結構

```text
.
├── AGENTS.md            # 本文件，供人類 & Codex 閱讀
├── scraper.py           # 程式主體，採用 Agent 架構
├── requirements.txt     # 相依套件清單
└── examples/
    └── output.json      # 執行範例輸出
```

---

## 快速開始

```bash
# 1. 建立虛擬環境 (建議)
python -m venv venv && source venv/bin/activate  # Windows 將 source 改為 .\venv\Scripts\activate

# 2. 安裝相依套件
pip install -r requirements.txt

# 3. 執行爬蟲
python scraper.py https://example.com --max-pages 30 --output examples/output.json
```

> **提示**：第一次執行請先選擇小型網站，避免誤觸大型站點防禦機制。

---

## 主要程式碼 (scraper.py)

以下列出最核心的部分，完整程式碼請見檔案本身。

```python
#!/usr/bin/env python3
"""
MiniSpider — 麻雀雖小、五臟俱全的教學爬蟲
------------------------------------------------
功能：
1. 指令列介面 (argparse)
2. Robots.txt 檢查
3. HTTP 例外處理 & 重試
4. 延遲 (1–2.5 秒隨機) 與變換 User-Agent
5. HTML 解析 (BeautifulSoup) — 抽取 <title> 與所有 <a> 連結
6. JSON 輸出 (路徑可自訂)
"""
import argparse, json, logging, random, sys, time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18 Safari/605.1.15",
]
DELAY_RANGE = (1, 2.5)  # 秒

# ------------------------ Agents ------------------------ #
class Fetcher:
    """負責下載頁面，並遵守 robots.txt 與延遲"""

    def __init__(self, session: requests.Session):
        self.session = session

    def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        rp = RobotFileParser()
        rp.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
        try:
            rp.read()
            return rp.can_fetch("*", url)
        except:  # robots.txt 不存在或讀取失敗
            return True

    def get(self, url: str, retries: int = 3) -> str | None:
        if not self.allowed(url):
            logging.warning("Blocked by robots.txt: %s", url)
            return None

        for attempt in range(1, retries + 1):
            try:
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                logging.debug("GET %s (attempt %d)" % (url, attempt))
                resp = self.session.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                time.sleep(random.uniform(*DELAY_RANGE))
                return resp.text
            except requests.RequestException as e:
                logging.error("%s (attempt %d)" % (e, attempt))
                if attempt == retries:
                    return None
                time.sleep(1)


class Parser:
    """解析 HTML，抽取標題與絕對連結"""

    def parse(self, html: str, base_url: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        title = (soup.title.string or "").strip() if soup.title else ""
        links = [urljoin(base_url, a.get("href")) for a in soup.find_all("a", href=True)]
        return {"title": title, "links": links}


class Saver:
    """將資料寫入 JSON 檔"""

    def __init__(self, outfile: Path):
        self.outfile = outfile
        self.outfile.parent.mkdir(parents=True, exist_ok=True)
        self.data: list[dict] = []

    def add(self, url: str, parsed: dict):
        self.data.append({"url": url, **parsed})

    def flush(self):
        self.outfile.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")


# ------------------------ Orchestrator ------------------------ #

def crawl(start_url: str, max_pages: int, outfile: str):
    session = requests.Session()
    fetcher = Fetcher(session)
    parser = Parser()
    saver = Saver(Path(outfile))

    frontier: list[str] = [start_url]
    visited: set[str] = set()

    while frontier and len(visited) < max_pages:
        url = frontier.pop(0)
        if url in visited:
            continue
        visited.add(url)

        html = fetcher.get(url)
        if not html:
            continue
        parsed = parser.parse(html, url)
        saver.add(url, parsed)
        logging.info("[%d/%d] %s" % (len(visited), max_pages, url))

        # 將同網域的新連結加入 frontier
        origin = urlparse(start_url).netloc
        for link in parsed["links"]:
            if urlparse(link).netloc == origin and link not in visited:
                frontier.append(link)

    saver.flush()


# ------------------------ CLI ------------------------ #

if __name__ == "__main__":
    argp = argparse.ArgumentParser(description="MiniSpider — 教學用多代理爬蟲")
    argp.add_argument("start_url", help="起始網址，例如：https://example.com")
    argp.add_argument("--max-pages", "-n", type=int, default=50, help="最大頁數 (預設 50)")
    argp.add_argument("--output", "-o", default="output.json", help="輸出檔案 (JSON)")
    argp.add_argument("--debug", action="store_true", help="顯示除錯訊息")
    args = argp.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        crawl(args.start_url, args.max_pages, args.output)
        logging.info("Done! Results saved to %s", args.output)
    except KeyboardInterrupt:
        logging.warning("Interrupted by user")
        sys.exit(130)
```

---

## 單元測試 (選擇性)

```python
# tests/test_parser.py
from scraper import Parser

def test_parse_title_and_links():
    html = """<html><head><title>Hello</title></head>
                 <body><a href='/a'>A</a><a href='https://b.com'>B</a></body></html>"""
    p = Parser()
    result = p.parse(html, "https://example.com")
    assert result["title"] == "Hello"
    assert "https://example.com/a" in result["links"]
```

執行：

```bash
pytest -q
```

---

## 擴充指南

| 想做的事 | 如何著手 |
| -------- | -------- |
| **支援更多資料格式 (e.g. JSON-LD)** | 改寫 `Parser.parse()`，加入相對應解析邏輯 |
| **將結果存入 SQLite** | 實作新的 `Saver` 子類別，例如 `SqliteSaver` |
| **並行抓取** | 引入 `asyncio` 或 `concurrent.futures`，並調整延遲邏輯 |
| **分散式排程** | 將 `frontier` 抽象化，改用 Redis 或 RabbitMQ |

---

## FAQ

> **Q**：為什麼不用 Scrapy？
>
> **A**：Scrapy 功能強大，但學習曲線較陡。本範例著重「看得懂」與「改得動」，待理解核心概念後，再升級至 Scrapy 也不遲。

> **Q**：需要遵守哪些網路爬蟲倫理？
>
> **A**：應先閱讀並尊重目標網站的使用條款與 robots.txt；避免過度頻繁請求；對自己行為負責。

---

## 版權宣告

本專案採用 MIT License 釋出，歡迎自由使用、修改與散佈；唯請保留作者資訊與本聲明。
