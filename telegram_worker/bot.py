# telegram_worker/bot.py
import os
import json
import asyncio
import logging
from datetime import datetime, timezone

import aiohttp
import telebot
from supabase import create_client

from telegram_worker.strategy_engine import (
    ROLL_BUFFER,
    api_color_to_name,
    evaluate,
    IMPRESSAO_RECENTE,
)

# ────────────────────────────────────────────────────────────────
# LOGGING
# ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bot-worker")

# ────────────────────────────────────────────────────────────────
# SUPABASE + TELEGRAM
# ────────────────────────────────────────────────────────────────
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
bot = telebot.TeleBot(os.getenv("TG_BOT_TOKEN"), parse_mode="Markdown")


# ────────────────────────────────────────────────────────────────
# PEQUENO FSM PARA CONTROLAR GALES E WIN/LOSS
# ────────────────────────────────────────────────────────────────
class GaleState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.gale            = 0            # 0 → 1 → 2
        self.estrategia      = None         # id
        self.estrategia_meta = {}           # dict com “sinal” / “gales”
        self.start_ts        = None         # datetime


STATE = GaleState()

# ----------------------------------------------------------------
# BUSCA O ÚLTIMO ROLL NA API EXTERNA
# ----------------------------------------------------------------
async def fetch_roll() -> dict:
    url = "https://elmovimento.vip/blaze_double/luk/index.json"
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession(timeout=timeout) as sess:
        async with sess.get(url) as r:
            r.raise_for_status()
            data = await r.json()
            head = data[0]
            result = {
                "roll":      head["roll"],
                "color_id":  head["color"],
                "color":     api_color_to_name(head["color"]),
                "timestamp": head["created_at"],
            }
            return result


# ----------------------------------------------------------------
# ENVIA MENSAGEM PARA TELEGRAM (placeholder simples)
# ----------------------------------------------------------------
def enviar_telegram(sig: dict) -> None:
    """Envia o texto do sinal para todos os canais do usuário"""
    chs = (
        sb.table("LUK_telegram_channels")
        .select("channel_id")
        .eq("user_id", sig["user_id"])
        .not_.is_("validated_at", None)
        .execute()
        .data
    )
    for ch in chs:
        bot.send_message(ch["channel_id"], sig["text"])


# ----------------------------------------------------------------
# VERIFICA SE O HEAD ATUAL FECHA WIN / LOSS / WHITE
# ----------------------------------------------------------------
def verifica_win(head: dict, state: GaleState) -> str | None:
    alvo = state.estrategia_meta.get("sinal")      # red/black/white
    if not alvo:
        return None

    cor = head["color"]
    if cor == alvo:
        return "WIN"
    if cor == "white":
        return "WHITE"

    # — não bateu: avança gale —
    state.gale += 1
    if state.gale > state.estrategia_meta.get("gales", 0):
        return "LOSS"
    return None


# ────────────────────────────────────────────────────────────────
# LOOP PRINCIPAL
# ────────────────────────────────────────────────────────────────
async def main_loop() -> None:
    while True:
        try:
            head = await fetch_roll()
            ROLL_BUFFER.append(head)

            log.info(
                "bot: Head ➜ roll %2d  cor %s   |  últimos: %s",
                head["roll"],
                head["color"],
                IMPRESSAO_RECENTE(),
            )

            # 1) procura sinais
            estrategias = sb.table("LUK_strategies").select("*").execute().data
            sinais = evaluate(estrategias)

            if sinais:
                for sig in sinais:
                    enviar_telegram(sig)
                    log.info(
                        "strategy: Sinal encontrado %s ➜ %s , Estratégia %s",
                        sig["sequence"],
                        sig["signal_color"],
                        sig["name"],
                    )
                    STATE.estrategia       = sig["strategy_id"]
                    STATE.estrategia_meta  = {
                        "sinal":  sig["signal_color"],
                        "gales":  2,
                    }
                    STATE.gale      = 0
                    STATE.start_ts  = datetime.now(timezone.utc)

            # 2) se houver estratégia ativa, verifica resultado
            if STATE.estrategia:
                res = verifica_win(head, STATE)
                if res:                       # WIN / LOSS / WHITE
                    sb.table("LUK_signals_log").insert({
                        "strategy_id": STATE.estrategia,
                        "result":      res,
                        "raw_payload": json.dumps(head),
                    }).execute()
                    log.info("bot: Resultado %s — resetando estado", res)
                    STATE.reset()

        except Exception:
            log.exception("bot: worker error")

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main_loop())
