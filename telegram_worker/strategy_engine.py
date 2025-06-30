"""Signal‑evaluation engine for Blaze Double.

This module keeps a 20‑item rolling buffer with the most‑recent results
coming from the public JSON endpoint and, on top of that, evaluates all
strategies stored in Supabase.

Supported strategy types
------------------------
* **color_sequence** – match a sequence of colours ("red", "black", "white").
  Use "*" as a wildcard for “any colour”.

    Example config::
        {
            "type": "color_sequence",
            "sequence": ["black", "black"],
            "signal": "red"
        }

* **number_sequence** – match a sequence of exact roll numbers and, when
  it occurs, suggest a target number.

    Example config::
        {
            "type": "number_sequence",
            "sequence": [8, 8],
            "signal": 14
        }

Returned signal objects are immediately consumable by **telegram_worker.bot**.
"""

from collections import deque
from typing import Any, Dict, List

# ──────────────────────────────────────────
# Runtime state (kept in memory inside the worker container)
# ──────────────────────────────────────────

#: last 20 rolls fetched from the public endpoint
ROLL_BUFFER: deque[Dict[str, Any]] = deque(maxlen=20)

#: remembers the last signal sent for each strategy so we don't spam
LAST_SIGNAL_BY_STRAT: dict[str, str] = {}

# ──────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────

def api_color_to_name(cid: int) -> str:
    """Map API colour id → human readable name."""
    return {0: "white", 1: "black", 2: "red"}.get(cid, "unknown")


# ──────────────────────────────────────────
# Public helpers (used by bot.py)
# ──────────────────────────────────────────

def remember_roll(roll: int) -> None:
    """Append a new roll to *ROLL_BUFFER*.

    The **bot** should call this **every time** it polls the JSON feed so that
    the buffer stays updated.
    """
    ROLL_BUFFER.append({
        "roll": roll,
        "color": api_color_to_name(roll_to_color_id(roll))
    })


def roll_to_color_id(roll: int) -> int:
    """Return the colour id (0/1/2) for a raw *roll* number (0‑14)."""
    if roll == 0:
        return 0  # white
    return 2 if roll <= 7 else 1  # 1‑7 red / 8‑14 black


def roll_to_color_name(roll: int) -> str:
    """Convenience wrapper that gives the colour *name* from a roll number."""
    return api_color_to_name(roll_to_color_id(roll))


# ──────────────────────────────────────────
# Core evaluation logic
# ──────────────────────────────────────────

def evaluate(strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compare every stored strategy against the current buffer.

    Parameters
    ----------
    strategies
        Raw rows returned from the ``LUK_strategies`` table.

    Returns
    -------
    list[dict]
        A list of *signal* dictionaries ready to be published.
    """
    signals: list[dict] = []

    if not ROLL_BUFFER:
        return signals

    # Prepare lists for quick slicing/matching
    recent_colors  = [r["color"] for r in ROLL_BUFFER]
    recent_numbers = [r["roll"]  for r in ROLL_BUFFER]

    for strat in strategies:
        cfg   = strat.get("config") or {}
        stype = cfg.get("type")

        # ------------------------------------------------------------
        # colour‑sequence strategies
        # ------------------------------------------------------------
        if stype == "color_sequence":
            seq   = cfg.get("sequence", [])          # e.g. ["black","black","*"]
            sig_c = cfg.get("signal", "unknown")
            if len(recent_colors) < len(seq):
                continue

            slice_colors = recent_colors[-len(seq):]
            matched = all(want == "*" or want == got for want, got in zip(seq, slice_colors))
            if not matched:
                continue

            # duplicate check --------------------------------------------------
            sig_key = f"{strat['id']}|{'+'.join(slice_colors)}"
            if LAST_SIGNAL_BY_STRAT.get(strat["id"]) == sig_key:
                continue  # identical signal already sent
            LAST_SIGNAL_BY_STRAT[strat["id"]] = sig_key
            # ------------------------------------------------------------------

            signals.append({
                "strategy_id": strat["id"],
                "user_id":     strat["user_id"],
                "result":      "+".join(slice_colors),
                "text": (
                    f"🎯 *Sinal* ➜ {sig_c.upper()}\n"
                    f"Sequência detectada: {' - '.join(slice_colors)}"
                )
            })

        # ------------------------------------------------------------
        # number‑sequence strategies
        # ------------------------------------------------------------
        elif stype == "number_sequence":
            seq   = cfg.get("sequence", [])           # e.g. [8, 8]
            sig_n = cfg.get("signal")                 # e.g. 14
            if len(recent_numbers) < len(seq):
                continue

            slice_nums = recent_numbers[-len(seq):]
            if slice_nums != seq:
                continue

            sig_key = f"{strat['id']}|{'+'.join(map(str, slice_nums))}"
            if LAST_SIGNAL_BY_STRAT.get(strat["id"]) == sig_key:
                continue
            LAST_SIGNAL_BY_STRAT[strat["id"]] = sig_key

            signals.append({
                "strategy_id": strat["id"],
                "user_id":     strat["user_id"],
                "result":      "+".join(map(str, slice_nums)),
                "text": (
                    f"🎯 *Sinal* ➜ {sig_n}\n"
                    f"Sequência numérica: {' - '.join(map(str, slice_nums))}"
                )
            })

    return signals
