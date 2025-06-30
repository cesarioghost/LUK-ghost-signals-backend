# telegram_worker/state.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class GaleState:
    """
    Mantém o ciclo de análise → sinal → gales → win/loss
    para UM usuário / estratégia por vez.
    """
    max_gales: int = 2
    ativa: bool = False
    gale_atual: int = 0
    estrategia: str | None = None
    disparada_em: datetime | None = None

    def dispara(self, estrategia: str):
        self.ativa        = True
        self.estrategia   = estrategia
        self.gale_atual   = 0
        self.disparada_em = datetime.utcnow()

    def proximo_gale(self) -> bool:
        """Incrementa.  True => ainda há gale; False => passou do limite"""
        self.gale_atual += 1
        return self.gale_atual <= self.max_gales

    def reset(self):
        self.__init__(max_gales=self.max_gales)  # volta ao default
