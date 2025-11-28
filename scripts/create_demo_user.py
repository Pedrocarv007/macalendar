"""
Script para criar usuário demo
"""
from app import create_app
from app.models.employee import Employee
from app.extensions.database import db

def create_demo_user():
    """Criar usuário demo"""
    app = create_app()
    
    with app.app_context():
        # Verificar se usuário demo já existe
        demo_employee = Employee.query.filter_by(email='demo@mac.com').first()
        
        if demo_employee:
            print("⚠️  Usuário demo já existe!")
            print(f"Email: {demo_employee.email}")
            print(f"Senha: demo123")
            return
        
        # Criar usuário demo
        demo = Employee(
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