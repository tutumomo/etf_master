# Source Health & Fetchability Matrix

| Source Domain               | Access Mode       | Recommended Tool          | Fetchability Score (1-5) | Notes                          | Last Checked       |
|-----------------------------|-------------------|---------------------------|--------------------------|--------------------------------|--------------------|
| finance.yahoo.com           | API               | `yfinance`                | 5                        | 穩定，需 API Key               | 2026-03-23         |
| www.twse.com.tw             | Web Scraping      | `requests` + `BeautifulSoup` | 3                        | 反爬蟲，需模擬瀏覽器行為       | 2026-03-23         |
| www.cnyes.com               | Web Scraping      | `requests` + `lxml`       | 4                        | 需處理 JavaScript              | 2026-03-23         |
| www.moneydj.com             | Web Scraping      | `selenium` (if available) | 2                        | 反爬蟲嚴重，需人工驗證         | 2026-03-23         |
| www.bloomberg.com           | API               | `requests` (unofficial)   | 3                        | 可能有 IP 封鎖                | 2026-03-23         |
| www.investing.com           | Web Scraping      | `requests` + `BeautifulSoup` | 4                        | 需處理 Cookie                  | 2026-03-23         |

---

## 更新紀錄
- **2026-03-23**：初始版本，由小鈴建立。

## 如何更新？
1. 直接編輯此檔案，或使用 `scripts/update_source_matrix.py`（待開發）。
2. 每次更新後，請同步更新 `Last Checked` 欄位。
3. 如果 Fetchability Score ≤ 2，請註明原因（例如：反爬蟲、需登入等）。