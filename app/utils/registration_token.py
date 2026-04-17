from flask_jwt_extended import create_access_token
from datetime import timedelta
import uuid


def create_registration_token(email, password, status):
    claims = {
        "type": "register",
        "email": email,
        "password_hash": password,
        "status": status,
        "system_code":"https://www.thecarv.com/mac/auth/callback",
        "nonce": str(uuid.uuid4())  # número aleatório preventivo de replay
    }

    token = create_access_token(
        identity=email,  # pode ser o email, ou um ID temporário
        additional_claims=claims,
        expires_delta=timedelta(minutes=30)
    )
    return token

