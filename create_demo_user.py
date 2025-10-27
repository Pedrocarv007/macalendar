"""
Script para criar usuário demo
"""
from app import create_app
from app.models.user import User
from app.extensions.database import db

def create_demo_user():
    """Criar usuário demo"""
    app = create_app()
    
    with app.app_context():
        # Verificar se usuário demo já existe
        demo_user = User.query.filter_by(email='demo@mac.com').first()
        
        if demo_user:
            print("⚠️  Usuário demo já existe!")
            print(f"Email: {demo_user.email}")
            print(f"Senha: demo123")
            return
        
        # Criar usuário demo
        demo = User(
            email="demo@mac.com",
            name="Usuário Demo",
            role="employee",
            department="Demo"
        )
        demo.set_password("demo123")
        
        db.session.add(demo)
        db.session.commit()
        
        print("✅ Usuário demo criado com sucesso!")
        print("📧 Email: demo@mac.com")
        print("🔑 Senha: demo123")
        print("👤 Role: employee")

if __name__ == "__main__":
    create_demo_user()