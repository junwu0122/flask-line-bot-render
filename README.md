# 📈 flask-line-bot-render  

一個結合 **LINE Bot + Flask + MongoDB** 的股票價格提醒系統。  
並將 **Web Service 架設在  Render 平台**\
使用者只需透過 LINE 輸入股票代號與條件，就能在價格達到目標時即時收到推播通知。  

---

## 🚀 功能特色
- ✅ **股票提醒**：輸入 `2330 高於 500` 就能設定提醒  
- ✅ **背景檢查**：系統會定期自動檢查股價  
- ✅ **即時通知**：達到條件後，透過 LINE 推播提醒  
- ✅ **避免重複**：同一股票代號會自動覆蓋舊條件  
- ✅ **查詢清單**：輸入 `列表` 查看目前追蹤的股票  
- ✅ **刪除提醒**：輸入 `刪除 2330` 移除追蹤  
- ✅ **資料儲存**：股票提醒資訊上傳至MongoDB可供查詢及記錄  
---

## 🛠️ 技術架構
- **後端框架**：Flask (Python)  
- **資料庫**：MongoDB (儲存提醒條件、通知狀態、最新股價)  
- **股價 API**：`yfinance` + `twstock`  
- **LINE Bot SDK**：Webhook & 推播通知  
- **部署**：Render  / 本地開發  

---

## 📂 專案結構
flask-line-bot-render/\
├── app.py # Flask 主程式 (LINE webhook & 背景檢查)\
├── price_checker.py # 股價抓取邏輯 (yfinance / twstock)\
├── stock_mongo.py # MongoDB CRUD (新增、查詢、刪除提醒)\
├── requirements.txt # Python 套件清單\
└── README.md # 專案說明文件

---

## ⚡ 使用方式

### 1. Clone 專案
```bash
git clone https://github.com/your-username/flask-line-bot-render.git
cd flask-line-bot-render
```
### 2. 安裝套件
```bash
pip install -r requirements.txt
```

### 3. 設定 .env 或 Render環境變數
```
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_存取權杖
LINE_CHANNEL_SECRET=你的_LINE_密鑰
LINE_USER_ID=你的_LINE_USER_ID
MONGO_URI=你的_MongoDB_連線字串
MONGO_COLLECTION_NAME=你的MongoDB collection名字
MONGO_DB_NAME=你的database名字
```
注意: 若使用Mongo Atlas時,建議按照以下步驟測試
- Atlas → Network Access → Add IP Address → 建議先填 0.0.0.0/0 測試（注意安全），或把 Render 提供的一組可用 IP 新增進去。

- 等待幾分鐘讓設定生效。



💬 LINE 指令範例

2330 高於 500 → 新增提醒

2330 低於 450 → 新增提醒

查詢/列表 → 查看提醒清單

刪除 2330 → 移除提醒

🔮 未來規劃

 - 支援「刪除單一條件」(例如 刪除 2330 高於 500)

 - 股票代號轉換公司名稱

-  即時查詢 K 線圖

 - 多用戶分帳管理
