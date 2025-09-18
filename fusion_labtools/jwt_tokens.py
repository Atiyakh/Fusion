# JWT tokens
import datetime
import jwt

# Load RSA private key from secure file
with open("private_key.pem", "rb") as my_very_secure_file:
    PRIVATE_KEY = my_very_secure_file.read()

# Load RSA public key
with open("public_key.pem", "rb") as my_file:
    PUBLIC_KEY = my_file.read()

def create_jwt_rs256(payload: dict, expires_in_seconds: int = 900) -> str:
    now = datetime.datetime.utcnow()
    exp = now + datetime.timedelta(seconds=expires_in_seconds)
    payload.update({
        "iat": now,
        "nbf": now,
        "exp": exp,
        "iss": ...,
        "aud": ...,
    })
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")

def verify_jwt_rs256(token: str) -> dict:
    return jwt.decode(
        token,
        PUBLIC_KEY,
        algorithms=["RS256"],
        audience=...,
        issuer=...,
        options={"require": ["exp", "iat", "nbf", "iss", "aud"]}
    )
