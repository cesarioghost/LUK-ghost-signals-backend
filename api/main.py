import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import create_engine, Session, select

from .models import Strategy
from .deps import get_current_user
from dotenv import load_dotenv
load_dotenv()


DATABASE_URL = os.getenv("SUPABASE_DB_URL")  # connection string completa
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

app = FastAPI(title="Ghost Signals API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health(): return {"ok": True}

@app.get("/strategies")
def list_strategies(user_id=Depends(get_current_user)):
    with Session(engine) as s:
        return s.exec(select(Strategy).where(Strategy.user_id == user_id)).all()

@app.post("/strategies")
def create_strategy(body: Strategy, user_id=Depends(get_current_user)):
    body.user_id = user_id
    with Session(engine) as s:
        s.add(body); s.commit(); s.refresh(body)
        return body
