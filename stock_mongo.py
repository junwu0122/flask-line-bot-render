from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

# 初始化 Mongo 連線
client = None
collection = None

try:
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,  # 5 秒 timeout
        tls=True,
        tlsAllowInvalidCertificates=True,  # ⚠️ 測試用，能連上再拿掉
    )
    # 測試連線
    client.admin.command("ping")
    print("[MongoDB] ✅ 連線成功")
    db = client["Jun"]
    collection = db["stock"]
except Exception as e:
    print(f"[MongoDB] ❌ 無法連線: {e}")
    try:
        line_bot_api.push_message(
            LINE_USER_ID,
            TextSendMessage(text=f"❌ 無法連線 MongoDB: {e}")
        )
    except Exception as line_err:
        print(f"[LINE 通知失敗] {line_err}")


def add_stock(stock_name, target_price, operator, current_price=None):
    """新增或更新股票提醒（同股票代號直接覆蓋舊的，並推播更新提示）"""
    if not collection:
        print("[add_stock] ❌ MongoDB 未連線")
        return

    doc = {
        "stock_name": stock_name,
        "target_price": float(target_price),
        "operator": operator,
        "current_price": current_price,
        "notified": False,
        "datetime": datetime.utcnow(),
    }

    try:
        result = collection.replace_one(
            {"stock_name": stock_name},  # ✅ 只比對股票代號
            doc,
            upsert=True,
        )

        print(
            f"[add_stock] stock={stock_name}, operator={operator}, target={target_price}, "
            f"matched={result.matched_count}, upserted_id={result.upserted_id}",
            flush=True,
        )

        # 如果 matched_count > 0，表示是覆蓋更新
        if result.matched_count > 0:
            try:
                line_bot_api.push_message(
                    LINE_USER_ID,
                    TextSendMessage(
                        text=f"⚠️ 股票 {stock_name} 的提醒條件已更新為 {operator} {target_price} (現價: {current_price})"
                    )
                )
            except Exception as e:
                print(f"❌ LINE 更新通知失敗: {e}")
    except Exception as e:
        print(f"[add_stock] ❌ MongoDB 操作失敗: {e}")


def get_stock():
    if not collection:
        print("[get_stock] ❌ MongoDB 未連線")
        return []
    try:
        return list(collection.find())
    except Exception as e:
        print(f"[get_stock] ❌ MongoDB 操作失敗: {e}")
        return []


def mark_notified(stock_id):
    """更新某一筆的 notified=True"""
    if not collection:
        print("[mark_notified] ❌ MongoDB 未連線")
        return
    try:
        collection.update_one(
            {"_id": ObjectId(stock_id)},
            {"$set": {"notified": True}}
        )
    except Exception as e:
        print(f"[mark_notified] ❌ MongoDB 操作失敗: {e}")


def delete_stock(stock_name):
    """刪除某股票的所有提醒"""
    if not collection:
        print("[delete_stock] ❌ MongoDB 未連線")
        return 0
    try:
        result = collection.delete_many({"stock_name": stock_name})
        return result.deleted_count
    except Exception as e:
        print(f"[delete_stock] ❌ MongoDB 操作失敗: {e}")
        return 0


def update_current_price(stock_name, price):
    """更新某股票的現價"""
    if not collection:
        print("[update_current_price] ❌ MongoDB 未連線")
        return
    try:
        collection.update_one(
            {"stock_name": stock_name},
            {"$set": {"current_price": price}}
        )
    except Exception as e:
        print(f"[update_current_price] ❌ MongoDB 操作失敗: {e}")
