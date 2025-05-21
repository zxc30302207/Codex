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
import argparse
import json
import logging
import random
import sys
import time
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
        except Exception:
            # robots.txt 不存在或讀取失敗
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
        self.outfile.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )


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
    argp.add_argument("--max-pages", "-n", type=int, default=50, help="最大頁數(預設 50)")
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
