"""
Script para debugar o problema do JWT
"""
from app import create_app
from flask_jwt_extended import create_access_token, decode_token
from app.models.user import User
import jwt

def debug_jwt():
    app = create_app()
    
    with app.app_context():
        print("=== DEBUG JWT ===")
        print(f"JWT_SECRET_KEY: {app.config['JWT_SECRET_KEY']}")
        
        # Buscar usuário demo
        user = User.query.filter_by(email='demo@mac.com').first()
        if not user:
            print("❌ Usuário demo não encontrado!")
            return
            
        print(f"✅ Usuário encontrado: {user.name} ({user.email})")
        
        # Criar token
        additional_claims = {
            'role': user.role,
            'restaurant_id': user.restaurant_id,
            'department': user.department,
            'name': user.name
        }
        
        token = create_access_token(
            identity=str(user.id),
            additional_claims=additional_claims
        )
        
        print(f"✅ Token criado: {token[:50]}...")
        
        # Tentar decodificar
        try:
            decoded = decode_token(token)
            print(f"✅ Token decodificado com sucesso!")
            print(f"   Sub: {decoded['sub']}")
            print(f"   Role: {decoded.get('role')}")
        except Exception as e:
            print(f"❌ Erro ao decodificar token: {e}")
            
        # Verificar com PyJWT diretamente
        try:
            decoded_direct = jwt.decode(
                token, 
                app.config['JWT_SECRET_KEY'], 
                algorithms=['HS256']
            )
            print(f"✅ PyJWT decodificação direta funcionou!")
        except Exception as e:
            print(f"❌ PyJWT erro: {e}")

if __name__ == "__main__":
    debug_jwt()