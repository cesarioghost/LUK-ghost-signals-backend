# telegram_worker/strategy_engine.py
from collections import deque
from typing import List, Dict, Any

# ------------------ BUFFER dos 20 últimos resultados ------------------
ROLL_BUFFER: deque[Dict[str, Any]] = deque(maxlen=20)   # cada item: roll+color


def api_color_to_name(cid: int) -> str:
    """Mapeia 0→white  1→black  2→red."""
    return {0: "white", 1: "black", 2: "red"}.get(cid, "unknown")


# ------------------ Avaliação das estratégias -------------------------
def evaluate(strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    signals: list[dict] = []
    if not ROLL_BUFFER:
        return signals

    recent_colors = [r["color"] for r in ROLL_BUFFER]
    recent_nums   = [r["roll"]  for r in ROLL_BUFFER]

    for strat in strategies:
        cfg   = strat.get("config") or {}
        stype = cfg.get("type")

        # ---- sequência de cores --------------------------------------
        if stype == "color_sequence":
            seq   = cfg["sequence"]            # p.ex. ["red","red","*"]
            sinal = cfg["signal"]              # cor a apostar

            if len(recent_colors) < len(seq):
                continue
            slice_colors = recent_colors[-len(seq):]

            match = all(w == "*" or w == g for w, g in zip(seq, slice_colors))
            if match:
                signals.append({
                    "strategy_id": strat["id"],
                    "user_id":     strat["user_id"],
                    "name":        strat["name"],
                    "sequence":    seq,
                    "signal_color": sinal,
                    "result":      "+".join(slice_colors),
                    "text": (
                        f"🎯 *Sinal* ➜ {sinal.upper()} "
                        f"(seq {seq} — último {'/'.join(slice_colors)})"
                    ),
                })

        # ---- sequência de números ------------------------------------
        elif stype == "number_sequence":
            seq   = cfg["sequence"]            # ex.: [8, 8]
            sinal = cfg["signal"]              # ex.: 14

            if len(recent_nums) < len(seq):
                continue
            slice_nums = recent_nums[-len(seq):]

            if slice_nums == seq:
                signals.append({
                    "strategy_id": strat["id"],
                    "user_id":     strat["user_id"],
                    "name":        strat["name"],
                    "sequence":    seq,
                    "signal_color": "num",
                    "result":      "+".join(map(str, slice_nums)),
                    "text": (
                        f"🎯 *Sinal* ➜ {sinal} "
                        f"(seq {seq} — último {'/'.join(map(str, slice_nums))})"
                    ),
                })

    return signals


# ------------------ impressão compacta p/ logs ------------------------
def IMPRESSAO_RECENTE() -> str:
    partes: list[str] = []
    for r in list(ROLL_BUFFER)[-20:]:
        emoji = "⚪" if r["color"] == "white" else ("🔴" if r["color"] == "red" else "⚫")
        partes.append(f"{r['roll']:2d}{emoji}")
    return " | ".join(partes)
