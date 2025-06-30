# telegram_worker/strategy_engine.py
from collections import deque
from typing import List, Dict, Any

# ────────────────────────────────────────────────────────────────
#  BUFFER DOS 20 ÚLTIMOS ROLLS RECEBIDOS
# ────────────────────────────────────────────────────────────────
# Cada item é: {"roll": int, "color_id": int, "color": str}
ROLL_BUFFER: deque[Dict[str, Any]] = deque(maxlen=20)


def api_color_to_name(cid: int) -> str:
    """Converte 0/1/2 do endpoint → white / black / red."""
    return {0: "white", 1: "black", 2: "red"}.get(cid, "unknown")


# ────────────────────────────────────────────────────────────────
#  AVALIA TODAS AS ESTRATÉGIAS
# ────────────────────────────────────────────────────────────────
def evaluate(strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analisa todas as estratégias cadastradas contra o ROLL_BUFFER
    e devolve os sinais prontos para disparar.
    """
    signals: list[dict] = []
    if not ROLL_BUFFER:
        return signals

    recent_colors  = [r["color"] for r in ROLL_BUFFER]
    recent_numbers = [r["roll"]  for r in ROLL_BUFFER]

    for strat in strategies:
        cfg   = strat.get("config") or {}
        stype = cfg.get("type")

        # ---------------------------------------------------------
        # SEQUÊNCIA DE CORES (P-P = V, V-V = P, etc.)
        # ---------------------------------------------------------
        if stype == "color_sequence":
            seq   = cfg["sequence"]        # ex.: ["black","black","*"]
            sig_c = cfg["signal"]          # black / red / white

            if len(recent_colors) < len(seq):
                continue
            slice_colors = recent_colors[-len(seq):]

            match = all(
                want == "*" or want == got
                for want, got in zip(seq, slice_colors)
            )
            if match:
                signals.append({
                    "strategy_id":  strat["id"],
                    "user_id":      strat["user_id"],
                    "name":         strat["name"],
                    "sequence":     seq,
                    "signal_color": sig_c,
                    "result":       "+".join(slice_colors),
                    "text": (
                        f"🎯 *Sinal* ➜ {sig_c.upper()} "
                        f"(seq {seq} — último {'/'.join(slice_colors)})"
                    ),
                })

        # ---------------------------------------------------------
        # SEQUÊNCIA DE NÚMEROS (8-8 = 14 …)
        # ---------------------------------------------------------
        elif stype == "number_sequence":
            seq   = cfg["sequence"]        # ex.: [8, 8]
            sig_n = cfg["signal"]          # 14

            if len(recent_numbers) < len(seq):
                continue
            slice_nums = recent_numbers[-len(seq):]

            if slice_nums == seq:
                signals.append({
                    "strategy_id":  strat["id"],
                    "user_id":      strat["user_id"],
                    "name":         strat["name"],
                    "sequence":     seq,
                    "signal_color": "num",
                    "result":       "+".join(map(str, slice_nums)),
                    "text": (
                        f"🎯 *Sinal* ➜ {sig_n} "
                        f"(seq {seq} — último {'/'.join(map(str, slice_nums))})"
                    ),
                })

    return signals


# ────────────────────────────────────────────────────────────────
#  IMPRESSÃO BONITA DOS 20 ÚLTIMOS RESULTADOS
# ────────────────────────────────────────────────────────────────
def IMPRESSAO_RECENTE() -> str:
    """Ex.: 12🔴 | 0⚪ | 5🔴 … (máx. 20 registros)"""
    partes: list[str] = []
    for r in list(ROLL_BUFFER)[-20:]:
        cor_emoji = "⚪" if r["color"] == "white" else (
            "🔴" if r["color"] == "red" else "⚫"
        )
        partes.append(f"{r['roll']:2d}{cor_emoji}")
    return " | ".join(partes)
