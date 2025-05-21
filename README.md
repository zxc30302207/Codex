# MiniSpider

這是一個簡潔的多代理爬蟲範例，搭配 `scraper.py` 展示如何以模組化的方式實作基本抓取、解析與儲存流程。

## 快速開始

```bash
# 1. 建立虛擬環境 (建議)
python -m venv venv && source venv/bin/activate  # Windows 將 source 改為 .\\venv\Scripts\activate

# 2. 安裝相依套件
pip install -r requirements.txt

# 3. 執行爬蟲
python scraper.py https://example.com --max-pages 30 --output examples/output.json
```

範例輸出請參考 `examples/output.json`。
