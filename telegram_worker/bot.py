import os, asyncio, json, aiohttp, telebot
from supabase import create_client
from telegram_worker.strategy_engine import evaluate

sb  = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
bot = telebot.TeleBot(os.getenv("TG_BOT_TOKEN"), parse_mode="Markdown")

async def fetch_roll():
    async with aiohttp.ClientSession() as sess:
        async with sess.get("https://elmovimiento.vip/blaze_double/luk/index.json") as r:
            data = await r.json()
            return data[0]["roll"]

async def loop():
    last = None
    while True:
        try:
            roll = await fetch_roll()
            if roll != last:
                last = roll
                strategies = sb.table("LUK_strategies").select("*").execute().data
                signals = evaluate(roll, strategies)
                for sig in signals:
                    channels = sb.table("LUK_telegram_channels") \
                                 .select("channel_id") \
                                 .eq("user_id", sig["user_id"]) \
                                 .not_.is_("validated_at", None) \
                                 .execute().data
                    for ch in channels:
                        bot.send_message(ch["channel_id"], sig["text"])
                    sb.table("LUK_signals_log").insert({
                        "strategy_id": sig["strategy_id"],
                        "result": sig["result"],
                        "raw_payload": json.dumps(sig)
                    }).execute()
        except Exception as e:
            print("worker error:", e)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(loop())
