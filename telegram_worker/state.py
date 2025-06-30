# telegram_worker/state.py
from dataclasses import dataclass
from datetime import datetime


@dataclass
class GaleState:
    """
    Mantém o ciclo sinal → gales → resultado
    PARA UMA estratégia de UM usuário.
    """
    max_gales: int = 2
    ativa: bool = False          # existe sinal “em aberto”?
    gale: int = 0                # 0 ▸ 1 ▸ 2 …
    estrategia_id: str | None = None      # UUID da strategy
    estrategia_meta: dict = None          # sinal/cores etc.
    start_ts: datetime | None = None      # quando foi disparado
    telegram_msg_ids: list[dict] = None   # msgs a apagar (+ tarde)

    def dispara(self, estrategia_id: str, meta: dict):
        self.ativa           = True
        self.estrategia_id   = estrategia_id
        self.estrategia_meta = meta
        self.gale            = 0
        self.start_ts        = datetime.utcnow()
        self.telegram_msg_ids = []

    def avanca_gale(self) -> bool:
        """True → ainda pode;  False → estourou limite"""
        self.gale += 1
        return self.gale <= self.max_gales

    def reset(self):
        self.__init__(max_gales=self.max_gales)     # volta ao default
