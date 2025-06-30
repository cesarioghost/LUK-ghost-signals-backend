# telegram_worker/bot.py
import os, asyncio, json, logging, aiohttp, telebot
from supabase import create_client

from telegram_worker.strategy_engine import (
    ROLL_BUFFER,          # deque global declarado no engine
    evaluate,             # devolve lista de sinais
    api_color_to_name     # 0/1/2 → "white"/"black"/"red"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bot-worker")

# credenciais
sb  = create_client(os.getenv("SUPABASE_URL"),   os.getenv("SUPABASE_SERVICE_KEY"))
bot = telebot.TeleBot(os.getenv("TG_BOT_TOKEN"), parse_mode="Markdown")

API_URL   = "https://elmovimiento.vip/blaze_double/luk/index.json"
TIMEOUT   = aiohttp.ClientTimeout(total=5)
INTERVAL  = 1          # seg

# ────────────────────────────────────────────────────────────────
async def fetch_recent() -> None:
    """Puxa os ~20 resultados, preenche ROLL_BUFFER e devolve cor+roll do head"""
    async with aiohttp.ClientSession(timeout=TIMEOUT) as sess:
        async with sess.get(API_URL) as r:
            r.raise_for_status()
            data = await r.json()          # ← lista de dicts (máx. 20)

    # limpa / re-preenche buffer com os NOVOS dados,
    # mais antigos primeiro – mais recente por último
    ROLL_BUFFER.clear()
    for item in reversed(data):            # garante ordem cronológica
        ROLL_BUFFER.append({
            "color_id": item["color"],     # 0,1,2
            "roll":     item["roll"],      # 0-14
            "color":    api_color_to_name(item["color"])
        })

    head = ROLL_BUFFER[-1]
    log.info("Head → roll %s  cor %s", head["roll"], head["color"])

# ────────────────────────────────────────────────────────────────
async def worker_loop():
    while True:
        try:
            await fetch_recent()

            # carrega TODAS as estratégias
            strategies = (
                sb.table("LUK_strategies")
                  .select("*")
                  .execute()
                  .data
            )

            signals = evaluate(strategies)
            log.info("Sinais gerados: %d", len(signals))

            for sig in signals:
                channels = (
                    sb.table("LUK_telegram_channels")
                      .select("channel_id")
                      .eq("user_id", sig["user_id"])
                      .not_.is_("validated_at", None)
                      .execute()
                      .data
                )
                for ch in channels:
                    bot.send_message(ch["channel_id"], sig["text"])

                sb.table("LUK_signals_log").insert({
                    "strategy_id": sig["strategy_id"],
                    "result":      sig["result"],
                    "raw_payload": json.dumps(sig)
                }).execute()

        except Exception:
            log.exception("worker error")

        await asyncio.sleep(INTERVAL)

if __name__ == "__main__":
    asyncio.run(worker_loop())
