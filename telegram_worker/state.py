# telegram_worker/state.py
from collections import deque
from datetime import datetime
from typing import Dict, Any, List


class GaleState:
    """
    Mantém:
      • buffer de até 20 rolls (número+cor)
      • controle de gale por estratégia
    """
    MAX_ROLLS = 20

    def __init__(self) -> None:
        self.buffer: deque[Dict[str, Any]] = deque(maxlen=self.MAX_ROLLS)
        # id_estratégia → {'count':0-2, 'sinal':cfg, 'ts':datetime}
        self.estrategia_meta: Dict[str, Dict[str, Any]] = {}

    # -----------------------  ROLLS  -----------------------
    def add_roll(self, roll: int, color: str) -> bool:
        """
        Adiciona o novo roll; devolve True caso seja realmente
        diferente do último (para podermos decidir se logamos).
        """
        if self.buffer and self.buffer[0]["roll"] == roll:
            return False  # dado repetido
        self.buffer.appendleft({"ts": datetime.utcnow(),
                                "roll": roll,
                                "color": color})
        return True

    def lista_cores(self) -> List[str]:
        return [r["color"] for r in self.buffer]

    def lista_nums(self) -> List[int]:
        return [r["roll"] for r in self.buffer]

    # --------------------  GALE / RESULT  ------------------
    def registrar_sinal(self, strat_id: str, sinal_cfg: Dict[str, Any]) -> None:
        self.estrategia_meta[strat_id] = {
            "count": 0,          # 0 = primeira, 1 = g1, 2 = g2
            "sinal": sinal_cfg,
            "ts": datetime.utcnow(),
        }

    def verificar_resultado(self, strat_id: str, ultimo_color: str) -> str | None:
        """
        Verifica se o sinal venceu / gale / perdeu.
        Retorna "WIN", "BRANCO", "LOSS" ou None (se ainda analisando).
        """
        meta = self.estrategia_meta.get(strat_id)
        if not meta:
            return None

        sinal_cor = meta["sinal"]["signal"]
        proteção_branco = True        # igual ao bot antigo
        count = meta["count"]

        # branco
        if ultimo_color == "white":
            if proteção_branco:
                meta["count"] = 0
                return "BRANCO"
            else:
                return "LOSS"

        # cor normal
        if ultimo_color == sinal_cor:
            meta["count"] = 0
            return "WIN"

        # não bateu -> gale
        meta["count"] += 1
        if meta["count"] > 2:
            meta["count"] = 0
            return "LOSS"

        # ainda há gales
        return None

    # utilitário para logs
    def rolls_formatado(self) -> str:
        nums = " , ".join(map(str, self.lista_nums()))
        return f"[{nums}]"

    def cores_formatado(self) -> str:
        cores = " , ".join(self.lista_cores())
        return f"[{cores}]"
