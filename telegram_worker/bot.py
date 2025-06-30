import os
import asyncio
import json
import logging
import aiohttp
import telebot
from supabase import create_client
from telegram_worker.strategy_engine import evaluate


# ────────────────  CONFIGURAÇÃO DE LOG  ────────────────
logging.basicConfig(
    level=logging.INFO,                       # ↓ mude para WARNING depois
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bot-worker")
# ───────────────────────────────────────────────────────


# Supabase e Bot
sb  = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
bot = telebot.TeleBot(os.getenv("TG_BOT_TOKEN"), parse_mode="Markdown")


async def fetch_roll() -> int:
    """Busca o último roll no endpoint externo"""
    url = "https://elmovimiento.vip/blaze_double/luk/index.json"
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession(timeout=timeout) as sess:
        async with sess.get(url) as r:
            r.raise_for_status()
            data = await r.json()
            roll = data[0]["roll"]
            log.info("Roll recebido: %s", roll)                # DEBUG
            return roll


async def loop() -> None:
    last = None
    while True:
        try:
            roll = await fetch_roll()
            if roll != last:
                last = roll
                strategies = sb.table("LUK_strategies").select("*").execute().data
                signals = evaluate(roll, strategies)
                log.info("Sinais gerados: %s", len(signals))   # DEBUG

                for sig in signals:
                    channels = (
                        sb.table("LUK_telegram_channels")
                          .select("channel_id")
                          .eq("user_id", sig["user_id"])
                          .not_.is_("validated_at", None)
                          .execute()
                          .data
                    )
                    log.info("Enviando para %d canais", len(channels))  # DEBUG

                    for ch in channels:
                        bot.send_message(ch["channel_id"], sig["text"])

                    sb.table("LUK_signals_log").insert({
                        "strategy_id": sig["strategy_id"],
                        "result":      sig["result"],
                        "raw_payload": json.dumps(sig)
                    }).execute()

        except Exception as e:
            log.exception("worker error")      # imprime stack-trace

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(loop())
