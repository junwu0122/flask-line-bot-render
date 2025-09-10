# price_checker.py
import yfinance as yf
import requests
import twstock
from datetime import datetime
from stock_mongo import update_current_price


def is_trading_time():
    """
    判斷是否為台股交易時間 (09:00 ~ 13:30)
    """
    now = datetime.now()
    return (now.hour > 9 or (now.hour == 9 and now.minute >= 0)) and (now.hour < 13 or (now.hour == 13 and now.minute <= 30))


def get_current_price(stock_id: str):
    """
    嘗試用 yfinance / twstock / twse API 取得即時股價
    收盤後 fallback -> 昨日收盤價
    """

    # ✅ 先檢查是不是交易時間
    trading = is_trading_time()

    # 如果是交易時間，優先嘗試即時股價
    if trading:
        # yfinance .TW
        try:
            ticker = yf.Ticker(f"{stock_id}.TW")
            data = ticker.history(period="1d", interval="1m")
            if not data.empty:
                current_price = round(data["Close"].iloc[-1], 2)
                print(f"✅ {stock_id}.TW (yfinance 即時) 現價: {current_price}")
                return current_price
        except Exception as e:
            print(f"❌ yfinance {stock_id}.TW 即時失敗: {e}")

        # twstock
        try:
            stock = twstock.realtime.get(stock_id)
            if stock and stock.get("success"):
                price = stock["realtime"].get("latest_trade_price")
                if price and price != "-":
                    current_price = float(price)
                    print(f"✅ {stock_id} (twstock) 現價: {current_price}")
                    return current_price
            print(f"❌ twstock 無法取得 {stock_id} 即時股價")
        except Exception as e:
            print(f"❌ twstock 取得 {stock_id} 失敗: {e}")

        # TWSE API
        try:
            url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_{stock_id}.tw"
            r = requests.get(url, timeout=5, verify=False)
            data = r.json()
            if "msgArray" in data and len(data["msgArray"]) > 0:
                price = data["msgArray"][0].get("z")
                if price and price != "-":
                    current_price = float(price)
                    print(f"✅ {stock_id} (twse api) 現價: {current_price}")
                    return current_price
            print(f"❌ twse api 無法取得 {stock_id} 即時股價")
        except Exception as e:
            print(f"❌ twse api 取得 {stock_id} 失敗: {e}")

    # 🚨 如果不是交易時間，或即時價都拿不到 → fallback 到昨日收盤
    try:
        ticker = yf.Ticker(f"{stock_id}.TW")
        data = ticker.history(period="5d")
        if not data.empty:
            close_price = round(data["Close"].iloc[-1], 2)
            print(f"🌙 {stock_id}.TW (收盤價 fallback) 昨日收盤: {close_price}")
            return close_price
    except Exception as e:
        print(f"❌ yfinance {stock_id}.TW 收盤價失敗: {e}")

    print(f"⚠️ 無法取得 {stock_id} 任何股價")
    return None


def check_price(stock_name, operator, target_price, current_price=None):
    """
    比對價格條件
    """
    try:
        if current_price is None:
            current_price = get_current_price(stock_name)

        if current_price is None:
            print(f"⚠️ 無法取得 {stock_name} 現價，跳過檢查")
            return False

        print(f"🔍 檢查 {stock_name} | 現價: {current_price} | 目標: {target_price} | 條件: {operator}")

        if operator == "greater_than":
            return current_price > target_price
        elif operator == "less_than":
            return current_price < target_price
        else:
            return False
    except Exception as e:
        print(f"❌ check_price 錯誤: {e}")
        return False


def refresh_and_update_price(stock_name):
    """
    強制抓最新價並更新 DB
    """
    current_price = get_current_price(stock_name)
    if current_price is not None:
        update_current_price(stock_name, current_price)
    return current_price
