# telegram_worker/bot.py
import os, json, asyncio, logging
from datetime import datetime, timezone

import aiohttp, telebot
from supabase import create_client

from telegram_worker.strategy_engine import (
    ROLL_BUFFER, api_color_to_name, evaluate, IMPRESSAO_RECENTE,
)
from telegram_worker.state import GaleState

# ------------------ logging ------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bot")

# ------------------ supabase + telegram -------
sb  = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
bot = telebot.TeleBot(os.getenv("TG_BOT_TOKEN"), parse_mode="Markdown")

STATE = GaleState()                       # controle de gale

# ------------------ fetch roll ----------------
async def fetch_roll() -> dict:
    url = "https://elmovimiento.vip/blaze_double/luk/index.json"
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession(timeout=timeout) as sess:
        async with sess.get(url) as r:
            r.raise_for_status()
            head = (await r.json())[0]
            return {
                "roll":  head["roll"],
                "color": api_color_to_name(head["color"]),
                "ts":    head["created_at"],
            }


# ------------------ telegram helper ----------
def enviar_telegram(uid: str, text: str):
    canais = (sb.table("LUK_telegram_channels")
                .select("channel_id")
                .eq("user_id", uid)
                .not_.is_("validated_at", None)
                .execute().data)
    for ch in canais:
        bot.send_message(ch["channel_id"], text)


# ------------------ win / gale / loss --------
def verifica_win(head: dict, st: GaleState) -> str | None:
    alvo = st.estrategia_meta.get("sinal")        # cor alvo
    if not alvo:
        return None

    cor = head["color"]
    if cor == alvo:
        return "WIN"
    if cor == "white":
        return "BRANCO"

    # não bateu: tenta gale
    if st.avanca_gale():
        return None
    return "LOSS"


# ------------------ main loop ----------------
async def main_loop():
    while True:
        try:
            head = await fetch_roll()
            ROLL_BUFFER.append(head)

            log.info("bot: Head ➜ roll %-2d  cor %-5s | %s",
                     head["roll"], head["color"], IMPRESSAO_RECENTE())

            # --------- gerar sinais ---------
            estrategias = sb.table("LUK_strategies").select("*").execute().data
            for sig in evaluate(estrategias):
                if STATE.ativa and sig["strategy_id"] == STATE.estrategia:
                    continue        # já acompanhando este sinal

                enviar_telegram(sig["user_id"], sig["text"])
                log.info("strategy: Sinal encontrado %s ➜ %s , Estratégia %s",
                         sig["sequence"], sig["signal_color"], sig["name"])

                STATE.dispara(sig["strategy_id"],
                              {"sinal": sig["signal_color"], "gales": 2})

                sb.table("LUK_signals_log").insert({
                    "strategy_id": sig["strategy_id"],
                    "result":      "LAUNCHED",
                    "raw_payload": json.dumps(sig),
                }).execute()

            # --------- verificar resultado ---
            if STATE.ativa:
                res = verifica_win(head, STATE)
                if res:
                    log.info("bot: Resultado %s — resetando", res)
                    sb.table("LUK_signals_log").insert({
                        "strategy_id": STATE.estrategia,
                        "result":      res,
                        "raw_payload": json.dumps(head),
                    }).execute()

                    enviar_telegram(os.getenv("TG_OWNER_ID"), f"Resultado: {res}")
                    STATE.reset()

        except Exception:
            log.exception("bot: worker error")

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main_loop())
