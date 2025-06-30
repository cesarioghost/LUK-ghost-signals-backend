# telegram_worker/bot.py
import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from collections import defaultdict

import aiohttp
import telebot
from supabase import create_client

from telegram_worker.strategy_engine import (
    ROLL_BUFFER,
    api_color_to_name,
    evaluate,
    pretty_recent,
)
from telegram_worker.state import GaleState

# ────────────────────────────────────────────────────────────────
#  LOGGING
# ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bot-worker")

# ────────────────────────────────────────────────────────────────
#  SUPABASE + TELEGRAM
# ────────────────────────────────────────────────────────────────
sb  = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
bot = telebot.TeleBot(os.getenv("TG_BOT_TOKEN"), parse_mode="Markdown")

# ────────────────────────────────────────────────────────────────
#  ESTADO POR USUÁRIO / ESTRATÉGIA
# ────────────────────────────────────────────────────────────────
states: dict[str, dict[str, GaleState]] = defaultdict(dict)
ultimo_ts: str | None = None               # p/ evitar spam de log


# ----------------------------------------------------------------
# BUSCA O ÚLTIMO ROLL DA API
# ----------------------------------------------------------------
async def fetch_roll() -> dict:
    url = "https://elmovimiento.vip/blaze_double/luk/index.json"
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession(timeout=timeout) as sess:
        async with sess.get(url) as r:
            r.raise_for_status()
            head = (await r.json())[0]
            return {
                "roll":      head["roll"],
                "color_id":  head["color"],
                "color":     api_color_to_name(head["color"]),
                "ts":        head["created_at"],
            }


# ----------------------------------------------------------------
# ENVIA MENSAGEM TELEGRAM (guarda id p/ apagar gale)
# ----------------------------------------------------------------
def enviar_telegram(user_id: str, texto: str) -> None:
    rows = (sb.table("LUK_telegram_channels")
              .select("channel_id")
              .eq("user_id", user_id)
              .not_.is_("validated_at", None)
              .execute()
              .data)
    for row in rows:
        msg = bot.send_message(row["channel_id"], texto)
        # grava p/ posterior deleção
        states[user_id]["_last_msg_ids"].append({
            "chat": row["channel_id"],
            "msg":  msg.message_id,
        })


# ----------------------------------------------------------------
# DEVOLVE STRATEGY_IDs COM RESULT == 'LAUNCHED' (sem WIN/LOSS/WHITE)
# ----------------------------------------------------------------
def sinais_ativos(user_id: str) -> set[str]:
    rows = (sb.table("LUK_signals_log")
              .select("strategy_id")
              .eq("user_id", user_id)
              .eq("result", "LAUNCHED")
              .execute()
              .data)
    return {r["strategy_id"] for r in rows}


# ----------------------------------------------------------------
# VERIFICA SE O ROLL ATUAL FECHA O SINAL
# ----------------------------------------------------------------
def verifica_result(head: dict, gs: GaleState) -> str | None:
    alvo = gs.estrategia_meta.get("sinal")       # red/black/white
    if not alvo:
        return None

    cor = head["color"]
    if cor == alvo:
        return "WIN"
    if cor == "white":
        return "WHITE"

    if not gs.avanca_gale():
        return "LOSS"
    return None      # segue no gale


# ────────────────────────────────────────────────────────────────
# LOOP PRINCIPAL
# ────────────────────────────────────────────────────────────────
async def main_loop() -> None:
    global ultimo_ts
    while True:
        try:
            head = await fetch_roll()
            if head["ts"] == ultimo_ts:          # mesmo head → ignora
                await asyncio.sleep(1)
                continue
            ultimo_ts = head["ts"]

            ROLL_BUFFER.append(head)
            log.info("bot: Head ➜ roll %2d  cor %s  |  %s",
                     head["roll"], head["color"], pretty_recent())

            # 1. carrega estratégias; separa por usuário
            estrategias = sb.table("LUK_strategies").select("*").execute().data
            estr_by_user: dict[str, list] = defaultdict(list)
            for e in estrategias:
                estr_by_user[e["user_id"]].append(e)

            # 2. percorre usuários
            for user_id, estr_list in estr_by_user.items():
                ativos = sinais_ativos(user_id)
                sinais = evaluate(estr_list, {user_id: ativos})

                # ───────── DISPARA NOVOS SINAIS ─────────
                for sig in sinais:
                    enviar_telegram(user_id, sig["text"])

                    sb.table("LUK_signals_log").insert({
                        "user_id":     user_id,
                        "strategy_id": sig["strategy_id"],
                        "result":      "LAUNCHED",
                        "raw_payload": json.dumps(sig),
                    }).execute()

                    gs = states[user_id].setdefault(
                        sig["strategy_id"], GaleState())
                    gs.dispara(sig["strategy_id"], {
                        "sinal": sig["signal_color"],
                        "gales": 2,
                    })

                # ───────── VERIFICA Gales / WIN / LOSS ─────────
                for strat_id, gs in list(states[user_id].items()):
                    if not gs.ativa or strat_id == "_last_msg_ids":
                        continue
                    res = verifica_result(head, gs)
                    if res:
                        # apaga mensagens de alerta/gale
                        for m in gs.telegram_msg_ids or []:
                            try:
                                bot.delete_message(m["chat"], m["msg"])
                            except Exception:
                                pass

                        sb.table("LUK_signals_log").insert({
                            "user_id":     user_id,
                            "strategy_id": strat_id,
                            "result":      res,
                            "raw_payload": json.dumps(head),
                        }).execute()
                        log.info("bot: Resultado %s  (user %s strat %s)",
                                 res, user_id, strat_id)
                        gs.reset()

        except Exception:
            log.exception("bot: worker error")

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main_loop())
#testes#
