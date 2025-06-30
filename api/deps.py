import os, jwt, requests
from fastapi import Header, HTTPException
from dotenv import load_dotenv
load_dotenv()


JWKS_URL = f"{os.getenv('SUPABASE_URL')}/auth/v1/keys"
_JWKS = requests.get(JWKS_URL).json()

def get_current_user(authorization: str = Header(...)):
    try:
        token = authorization.split()[1]
        header = jwt.get_unverified_header(token)
        key = next(k for k in _JWKS["keys"] if k["kid"] == header["kid"])
        data = jwt.decode(token, key, algorithms=["RS256"], audience="authenticated")
        return data["sub"]
    except Exception:
        raise HTTPException(401, "Invalid or missing JWT")
