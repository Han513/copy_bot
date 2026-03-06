# 文章輪巡一鍵跟單 Bot（Telegram）

本專案是一個 Telegram Bot：

- **輪巡後端接口** `POSTS_URL` 取得「未發布/未公告」文章（信號）
- 自動發佈到**公開頻道**，並附上 **「一鍵跟單」**按鈕（深連結跳轉私訊）
- 用戶在**私訊**完成確認流程：確認/修改/取消 → 輸入金額（檢查餘額）→ 輸入槓桿 → 提交

> 目前「提交」只會先落庫做佔位（`copy_orders`），後續你補上「綁定交易所帳號」後即可接真實下單。

---

## 安裝

```bash
pip install -r requirements.txt
```

---

## 設定

1) 複製 `.env.example` 成 `.env`
2) 填入以下變數：

- `TELEGRAM_BOT_TOKEN`
- `PUBLIC_CHANNEL_ID`（頻道 chat_id，例如 `-100xxxxxxxxxx`；Bot 需是頻道管理員）
- `POSTS_URL`（例如 `https://api.example.com/posts/list`）
- `POSTS_HEADERS_JSON`（可選，JSON 字串）
- `POLL_INTERVAL_SECONDS`（可選，預設 15）
- `DATABASE_URL`（可選，預設 sqlite；也可用 mysql）

---

## 啟動

在專案根目錄：

```bash
python -m src.main
```

或在 `src/` 目錄：

```bash
python main.py
```

---

## 私訊測試指令

- `/balance`：查詢餘額
- `/recharge 100`：充值（測試用）

---

## License

MIT，詳見 [LICENSE](LICENSE)
