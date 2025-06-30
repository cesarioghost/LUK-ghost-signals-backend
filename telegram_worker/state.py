# telegram_worker/state.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any


@dataclass
class GaleState:
    """
    Guarda o ciclo   sinal → gales → WIN/LOSS   de UMA estratégia ativa.
    """
    max_gales: int = 2                                      # 0 (primeira) + G1 + G2
    ativa: bool = False
    gale: int = 0                                           # 0 / 1 / 2
    estrategia: str | None = None                           # id da estratégia
    estrategia_meta: Dict[str, Any] = field(default_factory=dict)
    disparada_em: datetime | None = None

    # ------------- helpers -------------
    def dispara(self, estrategia: str, meta: Dict[str, Any]):
        """Começa a acompanhar uma nova estratégia."""
        self.ativa = True
        self.estrategia = estrategia
        self.estrategia_meta = meta
        self.gale = 0
        self.disparada_em = datetime.utcnow()

    def avanca_gale(self) -> bool:
        """True se ainda há gales disponíveis; False se estourou limite."""
        self.gale += 1
        return self.gale <= self.max_gales

    def reset(self):
        """Volta ao estado inicial."""
        self.ativa = False
        self.gale = 0
        self.estrategia = None
        self.estrategia_meta.clear()
        self.disparada_em = None
