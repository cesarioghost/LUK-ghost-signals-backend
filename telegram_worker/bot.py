# telegram_worker/bot.py
import os, asyncio, json, logging, aiohttp, telebot
from supabase import create_client
from telegram_worker.strategy_engine import (
    ROLL_BUFFER, api_color_to_name, evaluate
)
from telegram_worker.state import GaleState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bot")

sb  = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
bot = telebot.TeleBot(os.getenv("TG_BOT_TOKEN"), parse_mode="Markdown")

STATE = GaleState(max_gales=2)          # <- ajustável

async def fetch_roll() -> dict:
    url = "https://elmovimiento.vip/blaze_double/luk/index.json"
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession(timeout=timeout) as sess:
        async with sess.get(url) as r:
            r.raise_for_status()
            data = await r.json()
            rec  = {
                "roll":  data[0]["roll"],
                "color": api_color_to_name(data[0]["color"]),
            }
            log.info("Head ➜ roll %s  cor %s", rec["roll"], rec["color"])
            return rec

async def loop():
    while True:
        try:
            rec = await fetch_roll()
            ROLL_BUFFER.append(rec)

            strategies = sb.table("LUK_strategies").select("*").execute().data
            signals = evaluate(strategies)

            # ─── DISPARAR ───────────────────────────────────────────────
            if signals and not STATE.ativa:
                sig = signals[0]
                STATE.dispara(sig["strategy_id"])
                envia_para_canais(sig["text"])

            # ─── ACOMPANHAR RESULTADO ──────────────────────────────────
            if STATE.ativa and len(ROLL_BUFFER) >= 1:
                ultimo = ROLL_BUFFER[-1]
                resultado = verifica_win(ultimo, STATE)

                if resultado == "WIN":
                    log.info("✅✅ WIN ✅✅")
                    STATE.reset()

                elif resultado == "LOSS":
                    if STATE.proximo_gale():
                        log.info("Faça o %dº gale!", STATE.gale_atual)
                    else:
                        log.info("❌❌ LOSS ❌❌")
                        STATE.reset()

        except Exception:
            log.exception("worker error")

        await asyncio.sleep(0.8)        # ↓ ajuste fino

# ---------------------------------------------------------------------
def envia_para_canais(texto: str):
    canais = (
        sb.table("LUK_telegram_channels")
          .select("channel_id")
          .eq("validated_at", None, invert=True)
          .execute().data
    )
    for ch in canais:
        try:
            bot.send_message(ch["channel_id"], texto)
        except Exception as e:
            log.warning("[AVISO] Bot sem permissão em %s: %s", ch["channel_id"], e)

def verifica_win(ultimo, state: GaleState) -> str | None:
    """
    Exemplo simples:
    se sinal pediu BLACK e último é black → WIN
    se sinal pediu um número específico idem.
    """
    # Aqui você coloca a mesma lógica que já possui
    return None
# ---------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(loop())
