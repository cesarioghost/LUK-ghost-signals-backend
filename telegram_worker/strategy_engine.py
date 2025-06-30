# telegram_worker/strategy_engine.py
from typing import List, Dict, Any

def evaluate(roll: int, strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Gera sinais a partir do roll e das estratégias cadastradas."""
    signals: list[dict] = []

    for strat in strategies:
        cfg = strat["config"] or {}
        color  = cfg.get("color")
        entry  = cfg.get("entry_sequence")
        payout = cfg.get("payout_sequence")

        if color is None or entry is None or payout is None:
            continue  # estratégia mal-configurada

        # 🔻 Exemplo bobo só para provar
        if roll == 0 and color == "red":
            signals.append({
                "strategy_id": strat["id"],
                "user_id": strat["user_id"],
                "result": f"Entrar {color.upper()} com {entry}× gale e {payout}× payout",
                "text": f"*Sinal* ➜ {color.capitalize()} - entrada {entry}/{payout}"
            })

    return signals
