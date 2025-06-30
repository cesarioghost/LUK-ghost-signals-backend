import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import create_engine, Session, select

from .models import Strategy
from .deps import get_current_user
from dotenv import load_dotenv

load_dotenv()

# A URL completa de conexão ao seu banco (Postgres supabase)
DATABASE_URL = os.getenv("SUPABASE_DB_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

app = FastAPI(title="Ghost Signals API")

# Habilita CORS para o frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/strategies", response_model=list[Strategy])
def list_strategies(user_id=Depends(get_current_user)):
    """
    Retorna todas as estratégias cadastradas pelo usuário autenticado.
    """
    with Session(engine) as session:
        statement = select(Strategy).where(Strategy.user_id == user_id)
        return session.exec(statement).all()

@app.post("/strategies", response_model=Strategy)
def create_strategy(body: Strategy, user_id=Depends(get_current_user)):
    """
    Cria uma nova estratégia para o usuário autenticado.
    O campo `user_id` é sobrescrito pela identidade extraída do token.
    """
    body.user_id = user_id
    with Session(engine) as session:
        session.add(body)
        session.commit()
        session.refresh(body)
        return body
