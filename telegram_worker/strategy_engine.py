# telegram_worker/strategy_engine.py
from collections import deque
from typing import List, Dict, Any
import logging

log = logging.getLogger("strategy")

ROLL_BUFFER: deque[Dict[str, Any]] = deque(maxlen=20)

def api_color_to_name(cid: int) -> str:
    return {0: "white", 1: "black", 2: "red"}.get(cid, "unknown")

def evaluate(strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    signals: list[dict] = []
    if not ROLL_BUFFER:
        return signals

    # DEBUG – mostra sempre os 20 últimos
    recent_colors  = [r["color"] for r in ROLL_BUFFER]
    recent_numbers = [r["roll"]  for r in ROLL_BUFFER]
    log.debug("Últimos números: %s", recent_numbers)
    log.debug("Últimas cores  : %s", recent_colors)

    for strat in strategies:
        cfg = strat.get("config") or {}
        t   = cfg.get("type")

        if t == "color_sequence":
            seq = cfg["sequence"]
            if recent_colors[-len(seq):] == seq:
                sig_color = cfg["signal"]
                log.info("Sinal encontrado %s ➜ %s , Estrategia %s",
                         seq, sig_color, strat["name"])
                signals.append({
                    "strategy_id": strat["id"],
                    "user_id":     strat["user_id"],
                    "text": (
                        f"🎯 *Sinal* ➜ {sig_color.upper()} "
                        f"(sequência {seq})"
                    ),
                    "meta": {"tipo": "cor", "esperado": seq, "sinal": sig_color}
                })

        elif t == "number_sequence":
            seq = cfg["sequence"]
            if recent_numbers[-len(seq):] == seq:
                sig_num = cfg["signal"]
                log.info("Sinal (números) %s ➜ %s , Estrategia %s",
                         seq, sig_num, strat["name"])
                signals.append({
                    "strategy_id": strat["id"],
                    "user_id":     strat["user_id"],
                    "text": (
                        f"🎯 *Sinal* ➜ {sig_num} "
                        f"(sequência {seq})"
                    ),
                    "meta": {"tipo": "num", "esperado": seq, "sinal": sig_num}
                })

    log.info("Sinais gerados: %d", len(signals))
    return signals
