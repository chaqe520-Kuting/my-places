# 我的地圖口袋名單

僅供個人使用（私人儲存庫，不開 GitHub Pages）。頁面：私人 Claude 頁面 https://claude.ai/artifact/5xuabc8SaaA5RLpMPWL6Qp

Google 地圖「已儲存」地點的分類查詢頁。

## 更新方式
- 資料：`places.json`
- 自動更新：Google Takeout 每 2 個月匯出「已儲存」到 Google 雲端硬碟，Claude 排程任務每月檢查最新的 takeout-*.zip，執行
  `python3 tools/update.py <takeout.zip> "<來源說明>"` 後推送到 main，再發布到私人 Claude 頁面。
- 已分類的地點保留原分類；新地點依關鍵字自動分類（頁面上標 🆕）；已從 Google 地圖刪除的地點會移除。
