# telegram_worker/strategy_engine.py
from typing import List, Dict, Any

def roll_to_color(roll: int) -> str:
    """0→white · 1-7→red · 8-14→black"""
    if roll == 0:
        return "white"
    elif 1 <= roll <= 7:
        return "red"
    return "black"


def evaluate(roll: int, strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Recebe o número sorteado e todas as estratégias cadastradas
    e devolve uma lista de sinais prontos para disparar.
    """
    color = roll_to_color(roll)
    signals: list[dict] = []

    for strat in strategies:
        cfg = strat.get("config") or {}

        if (
            color == cfg.get("color") and
            roll  == cfg.get("entry_sequence")
        ):
            # exemplo – ajuste/adicione gales, payouts etc.
            signals.append({
                "strategy_id": strat["id"],
                "user_id": strat["user_id"],
                "result": f"{color}-{roll}",
                "text": (
                    f"🎯 *Sinal* ➜ {color.capitalize()} – "
                    f"entrada {cfg['entry_sequence']} / {cfg['payout_sequence']}"
                )
            })

    return signals
