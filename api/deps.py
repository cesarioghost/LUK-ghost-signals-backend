# api/deps.py

import os
import time
import jwt
import requests
from fastapi import Header, HTTPException
from dotenv import load_dotenv

load_dotenv()

# URL para buscar as chaves públicas do Supabase Auth
JWKS_URL = f"{os.getenv('SUPABASE_URL')}/auth/v1/keys"

# Cache simples em memória das chaves JWKS, com expiração
_JWKS: dict | None = None
_JWKS_LAST_FETCH: float = 0.0
_JWKS_TTL = 60 * 60  # 1 hora


def _get_jwks() -> dict:
    """
    Busca (ou retorna cache) do conjunto de chaves JWKS.
    Faz re­fetch após o TTL expirar.
    """
    global _JWKS, _JWKS_LAST_FETCH

    now = time.time()
    if _JWKS is None or (now - _JWKS_LAST_FETCH) > _JWKS_TTL:
        resp = requests.get(JWKS_URL, timeout=5)
        if resp.status_code != 200:
            raise HTTPException(503, detail="Não foi possível obter as chaves de autenticação.")
        _JWKS = resp.json()
        _JWKS_LAST_FETCH = now

    return _JWKS


def get_current_user(authorization: str = Header(...)) -> str:
    """
    Extrai e valida o JWT enviado no header Authorization.
    Retorna o 'sub' (user_id) se válido, ou levanta 401 caso contrário.
    Exemplo de header: "Authorization: Bearer <token>"
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, detail="Cabeçalho Authorization inválido.")

    token = authorization.split(" ", 1)[1]

    try:
        unverified_hdr = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise HTTPException(401, detail="Token malformado.")

    jwks = _get_jwks()
    key = next((k for k in jwks.get("keys", []) if k["kid"] == unverified_hdr.get("kid")), None)
    if key is None:
        raise HTTPException(401, detail="Chave de assinatura não encontrada.")

    try:
        # audience 'authenticated' é o default do Supabase para usuários logados
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience="authenticated",
            options={"verify_exp": True}
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, detail="Token expirado.")
    except jwt.InvalidAudienceError:
        raise HTTPException(401, detail="Audience inválido no token.")
    except jwt.PyJWTError:
        raise HTTPException(401, detail="Falha na validação do token.")

    # 'sub' contém o UUID do usuário no Supabase
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, detail="Token não contém subject (sub).")

    return user_id
