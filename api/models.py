from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB          # 👈
from uuid import UUID, uuid4
from datetime import datetime
from typing import Any, Dict

class Strategy(SQLModel, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID
    name: str
    game_type: str

    # armazena sequência, gales, etc. em jsonb
    config: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB)                            # 👈
    )

    created_at: datetime | None = Field(default_factory=datetime.utcnow)
