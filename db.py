import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB_NAME", "stock_db")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "stocks")

# 用全域 client 避免重複連線
_client = None

def init_mongo_db():
    global _client
    if _client is None:
        try:
            _client = MongoClient(MONGO_URI)
            print(f"✅ [Mongo] 成功連線到 {MONGO_URI}")
        except Exception as e:
            print(f"❌ [Mongo] 無法連線: {e}")
            raise
    db = _client[DB_NAME]
    return db[COLLECTION_NAME]
def get_collection():
    """
    取得 MongoDB 的 collection，lazy load 方式建立 Client。
    每次呼叫都確保能拿到 thread-safe 的連線。
    """
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, connect=False)  # ✅ fork-safe
    return _client[DB_NAME][COLLECTION_NAME]