import os
import threading
import time
import sys
from flask import Flask, request, abort
from dotenv import load_dotenv
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from price_checker import check_price, get_current_price
from stock_mongo import add_stock, get_stock, mark_notified, update_current_price
from stock_mongo import delete_stock

load_dotenv()

app = Flask(__name__)

# 讓 print 即時 flush 到 Render logs
sys.stdout.reconfigure(line_buffering=True)

# LINE config
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    parts = text.split()

    # 📋 查詢提醒列表
    if text in ["列表", "查詢", "list"]:
        stocks = get_stock()
        if not stocks:
            reply_text = "📭 目前沒有任何股票提醒"
        else:
            lines = []
            for s in stocks:
                op = "高於" if s["operator"] == "greater_than" else "低於"
                notified = "✅ 已通知" if s.get("notified") else "⏳ 未通知"
                current = s.get("current_price", "N/A")
                lines.append(f"{s['stock_name']} {op} {s['target_price']} | 現價 {current} | {notified}")
            reply_text = "📋 提醒清單：\n" + "\n".join(lines)

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text),
        )
        return

    # ❌ 刪除提醒
    if text.startswith("刪除 "):
        stock_id = text.replace("刪除", "").strip()
        deleted_count = delete_stock(stock_id)
        if deleted_count > 0:
            reply_text = f"🗑️ 已刪除 {deleted_count} 筆 {stock_id} 的提醒"
        else:
            reply_text = f"⚠️ 找不到 {stock_id} 的提醒"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return

    # ⚡ 設定提醒
    if len(parts) == 3:
        stock_id, operator, target_price = parts

        # 支援中文 & 符號
        if operator in ["低於", "小於", "<"]:
            operator = "less_than"
        elif operator in ["高於", "大於", ">"]:
            operator = "greater_than"
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ 請輸入 低於/高於 或 < / >"),
            )
            return

        try:
            target_price = float(target_price)
        except ValueError:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="⚠️ 目標價格必須是數字")
            )
            return

        # 取得現價
        current_price = get_current_price(stock_id)

        # 新增/更新到 MongoDB（避免重複）
        add_stock(
            stock_id,
            target_price,
            operator,
            current_price=current_price,
        )

        print(
            f"✅ 已設定提醒 {stock_id} {operator} {target_price}, 現價 {current_price}",
            flush=True,
        )

        # 回覆用戶
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"✅ 已設定股票 {stock_id}\n條件: {operator} {target_price}\n現價: {current_price}"
            ),
        )

        # ⚡ 新增後立即檢查一次條件
        if current_price is not None:
            condition_hit = False
            if operator == "less_than" and current_price < target_price:
                condition_hit = True
            elif operator == "greater_than" and current_price > target_price:
                condition_hit = True

            if condition_hit:
                try:
                    line_bot_api.push_message(
                        os.getenv("LINE_USER_ID"),
                        TextSendMessage(
                            text=f"📢 {stock_id} 已立即達到條件 {operator} {target_price}！\n現價: {current_price}"
                        ),
                    )
                    # 直接標記為已通知
                    stocks = get_stock()
                    for s in stocks:
                        if (
                            s["stock_name"] == stock_id
                            and s["operator"] == operator
                            and s["target_price"] == target_price
                        ):
                            mark_notified(s["_id"])
                            print(f"[立即通知] 已標記 {stock_id} 為已通知")
                            break
                except Exception as e:
                    print(f"❌ LINE 立即通知失敗: {e}")

    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="請輸入格式：\n股票代號 低於/高於 目標價格\n例如：2330 低於 500\n\n其他指令：\n📋 列表 → 查看提醒清單\n🗑️ 刪除 2330 → 移除提醒"
            ),
        )


def process_stock():
    """背景執行：定期檢查價格"""
    while True:
        stocks = get_stock()
        for s in stocks:
            stock_id = str(s["_id"])
            stock_name = s["stock_name"]
            operator = s["operator"]
            target_price = s["target_price"]
            current_price = get_current_price(stock_name)
            update_current_price(stock_name, current_price)

            notified = s.get("notified", False)
            print(
                f"[檢查] {stock_name}, 現價={current_price}, 條件={operator} {target_price}, 已通知={notified}"
            )

            if current_price is not None and not notified:
                if (operator == "less_than" and current_price < target_price) or (
                    operator == "greater_than" and current_price > target_price
                ):
                    try:
                        line_bot_api.push_message(
                            os.getenv("LINE_USER_ID"),
                            TextSendMessage(
                                text=f"📢 {stock_name} 已達到條件 {operator} {target_price}！\n現價: {current_price}"
                            ),
                        )
                        mark_notified(stock_id)
                        print(f"[背景檢查] 已標記 {stock_name} 為已通知")
                    except Exception as e:
                        print(f"❌ LINE 通知失敗: {e}")

        print("[等待] 下一輪檢查...")
        time.sleep(60)  # 每分鐘檢查一次


if __name__ == "__main__":
    print("[初始化] 啟動立即檢查一次股票條件")
    process_stock_thread = threading.Thread(target=process_stock, daemon=True)
    process_stock_thread.start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))