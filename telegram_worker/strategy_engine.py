# telegram_worker/strategy_engine.py
from collections import deque
from typing import List, Dict, Any

# guarda máx. 20 registros (cada um é {"roll":n,"color_id":c,"color":str})
ROLL_BUFFER: deque[Dict[str,Any]] = deque(maxlen=20)

def api_color_to_name(cid: int) -> str:
    """Mapeia 0/1/2 do endpoint para names human-readable."""
    return {0: "white", 1: "black", 2: "red"}.get(cid, "unknown")

# -----------------------------------------------------------------------------
def evaluate(strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analisa todas as estratégias cadastradas contra o ROLL_BUFFER
    e devolve os sinais prontos para disparar.
    """
    signals: list[dict] = []
    if not ROLL_BUFFER:
        return signals

    # listas auxiliares para comparação
    recent_colors  = [r["color"] for r in ROLL_BUFFER]
    recent_numbers = [r["roll"]  for r in ROLL_BUFFER]

    for strat in strategies:
        cfg   = strat.get("config") or {}
        stype = cfg.get("type")

        if stype == "color_sequence":         # ----------------------------
            seq   = cfg["sequence"]           # ["black","black","*"]…
            sig_c = cfg["signal"]
            if len(recent_colors) < len(seq):
                continue
            slice_colors = recent_colors[-len(seq):]

            match = all(
                want == "*" or want == got
                for want, got in zip(seq, slice_colors)
            )
            if match:
                signals.append({
                    "strategy_id": strat["id"],
                    "user_id":     strat["user_id"],
                    "result":      "+".join(slice_colors),
                    "text": (
                        f"🎯 *Sinal* ➜ {sig_c.upper()} "
                        f"(seq {seq} — último {'/'.join(slice_colors)})"
                    )
                })

        elif stype == "number_sequence":      # ----------------------------
            seq   = cfg["sequence"]           # [8,8]
            sig_n = cfg["signal"]             # 14
            if len(recent_numbers) < len(seq):
                continue
            slice_nums = recent_numbers[-len(seq):]

            if slice_nums == seq:
                signals.append({
                    "strategy_id": strat["id"],
                    "user_id":     strat["user_id"],
                    "result":      "+".join(map(str, slice_nums)),
                    "text": (
                        f"🎯 *Sinal* ➜ {sig_n} "
                        f"(seq {seq} — último {'/'.join(map(str,slice_nums))})"
                    )
                })

    return signals
