# telegram_worker/strategy_engine.py
from collections import deque
from typing import List, Dict, Any, DefaultDict

# ────────────────────────────────────────────────────────────────
#  BUFFER DOS 20 ÚLTIMOS ROLLS
# ────────────────────────────────────────────────────────────────
# Cada item: {"roll":int, "color_id":int, "color":str}
ROLL_BUFFER: deque[Dict[str, Any]] = deque(maxlen=20)


def api_color_to_name(cid: int) -> str:
    """0/1/2  →  white / black / red"""
    return {0: "white", 1: "black", 2: "red"}.get(cid, "unknown")


# ────────────────────────────────────────────────────────────────
#  AVALIA TODAS AS ESTRATÉGIAS
# ────────────────────────────────────────────────────────────────
def evaluate(
    strategies: List[Dict[str, Any]],
    launched_by_user: Dict[str, set],
) -> List[Dict[str, Any]]:
    """
    Compara as estratégias com o ROLL_BUFFER e devolve
    os sinais prontos para disparar.
    `launched_by_user[user_id]`  contém strategy_id já disparadas
    e ainda sem WIN/LOSS/WHITE → não dispara de novo.
    """
    signals: list[dict] = []
    if not ROLL_BUFFER:
        return signals

    recent_colors  = [r["color"] for r in ROLL_BUFFER]
    recent_numbers = [r["roll"]  for r in ROLL_BUFFER]

    for strat in strategies:
        if strat["id"] in launched_by_user.get(strat["user_id"], set()):
            continue                                # sinal ativo – ignora

        cfg   = strat.get("config") or {}
        stype = cfg.get("type")

        # ---------------------------------------------------------#
        # 1. SEQUÊNCIA DE CORES                                    #
        # ---------------------------------------------------------#
        if stype == "color_sequence":
            seq   = cfg["sequence"]                # ["black","black","*"]
            sig_c = cfg["signal"]                  # black/red/white

            if len(recent_colors) < len(seq):
                continue
            slice_colors = recent_colors[-len(seq):]

            if all(w == "*" or w == g for w, g in zip(seq, slice_colors)):
                signals.append({
                    "strategy_id":  strat["id"],
                    "user_id":      strat["user_id"],
                    "name":         strat["name"],
                    "signal_color": sig_c,
                    "sequence":     seq,
                    "result":       "+".join(slice_colors),
                    "text": (
                        f"🎯 *Sinal* ➜ {sig_c.upper()}  "
                        f"(seq {seq} — último {'/'.join(slice_colors)})"
                    ),
                })

        # ---------------------------------------------------------#
        # 2. SEQUÊNCIA DE NÚMEROS                                  #
        # ---------------------------------------------------------#
        elif stype == "number_sequence":
            seq   = cfg["sequence"]                # [8, 8]
            sig_n = cfg["signal"]                  # 14

            if len(recent_numbers) < len(seq):
                continue
            slice_nums = recent_numbers[-len(seq):]

            if slice_nums == seq:
                signals.append({
                    "strategy_id":  strat["id"],
                    "user_id":      strat["user_id"],
                    "name":         strat["name"],
                    "signal_color": "num",
                    "sequence":     seq,
                    "result":       "+".join(map(str, slice_nums)),
                    "text": (
                        f"🎯 *Sinal* ➜ {sig_n}  "
                        f"(seq {seq} — último {'/'.join(map(str, slice_nums))})"
                    ),
                })

    return signals


# ────────────────────────────────────────────────────────────────
#  FORMATAÇÃO BONITA PARA LOG
# ────────────────────────────────────────────────────────────────
def pretty_recent() -> str:
    partes: list[str] = []
    for r in list(ROLL_BUFFER)[-20:]:
        emoji = "⚪" if r["color"] == "white" else (
                "🔴" if r["color"] == "red" else "⚫")
        partes.append(f"{r['roll']:2d}{emoji}")
    return " | ".join(partes)
