from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "stocks")  # 預設 stocks
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "stock_db")  # 預設 stock_db

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

# 建立 MongoDB 連線
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tls=True)
    client.admin.command("ping")
    print("✅ 成功連線 MongoDB Atlas")
except Exception as e:
    print(f"❌ MongoDB 連線失敗: {e}")

db = client[MONGO_DB_NAME]
collection = db[MONGO_COLLECTION_NAME]

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

def add_stock(stock_name, target_price, operator, current_price=None):
    """新增或更新股票提醒（同股票代號直接覆蓋舊的，並推播更新提示）"""
    doc = {
        "stock_name": stock_name,
        "target_price": float(target_price),
        "operator": operator,
        "current_price": current_price,
        "notified": False,
        "datetime": datetime.utcnow(),
    }

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


def get_stock():
    return list(collection.find())


def mark_notified(stock_id):
    """更新某一筆的 notified=True"""
    collection.update_one(
        {"_id": ObjectId(stock_id)},
        {"$set": {"notified": True}}
    )


def delete_stock(stock_name):
    """刪除某股票的所有提醒"""
    result = collection.delete_many({"stock_name": stock_name})
    return result.deleted_count


def update_current_price(stock_name, price):
    """更新某股票的現價"""
    collection.update_one(
        {"stock_name": stock_name},
        {"$set": {"current_price": price}}
    )
