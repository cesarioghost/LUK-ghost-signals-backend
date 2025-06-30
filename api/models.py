from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from uuid import UUID, uuid4
from datetime import datetime
from typing import Any, Dict

class Strategy(SQLModel, table=True):
    """
    Representa uma regra de palpite do usuário:
      - `config` guarda a sequência (cores ou números) e o sinal a ser disparado.
      - Usamos JSONB no Postgres para flexibilidade.
    """
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")  # FK para tabela de usuários (se existir)
    name: str
    game_type: str

    # Armazena qualquer JSON (sequência, signal, etc.) em coluna JSONB
    config: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB)
    )

    created_at: datetime | None = Field(default_factory=datetime.utcnow)
