"""Script para criar usuários demo com todos os roles disponíveis."""
import sys
import os
from datetime import date

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import dotenv
loadenv = dotenv.load_dotenv()
from app import create_app
from app.models.employee import Employee
from app.models.restaurant import Restaurant
from app.extensions.database import db

def create_demo_users():
    """Criar usuários demo com todos os roles"""
    app = create_app()
    
    with app.app_context():
        # Criar restaurante demo se não existir
        restaurant = Restaurant.query.filter_by(name='Oeiras A5').first()
        if not restaurant:
            restaurant = Restaurant(
                name='Oeiras A5',
                address='Rua do Demo, 123',
                phone='910000000',
                email='demo-restaurant@mac.com',
                is_active=True
            )
            db.session.add(restaurant)
            db.session.commit()
            print("✅ Restaurante Demo criado")
        
        # Definir usuários demo para cada role
        demo_users = [
            {
                'email': 'admin@gmail.com',
                'name': 'Pedro Carvalho',
                'role': 'admin',
                'department': 'Administração',
                'position': 'Administrador do Sistema',
            },
        ]

        print("\n🔧 Criando usuários demo...\n")
        created_count = 0
        skipped_count = 0

        for user_data in demo_users:
            # Verificar se usuário já existe
            existing = Employee.query.filter_by(email=user_data['email']).first()
            
            if existing:
                print(f"⚠️  {user_data['name']} já existe (email: {user_data['email']})")
                skipped_count += 1
                continue

            # Criar usuário
            employee = Employee(
                email=user_data['email'],
                name=user_data['name'],
                role=user_data['role'],
                department=user_data['department'],
                position=user_data['position'],
                birth_date=date(1990, 1, 1),
                restaurant_id=restaurant.id,
                is_active=True
            )
            
            db.session.add(employee)
            created_count += 1
            
            print(f"✅ {user_data['name']} criado")
            print(f"   📧 Email: {user_data['email']}")
            print(f"   👤 Role: {user_data['role']}\n")

        if created_count > 0:
            db.session.commit()
            print(f"\n🎉 {created_count} usuário(s) demo criado(s) com sucesso!")
        
        if skipped_count > 0:
            print(f"⏭️  {skipped_count} usuário(s) já existente(s)")

        print("\n📋 Resumo dos usuários demo disponíveis:")
        print("=" * 60)
        for user_data in demo_users:
            print(f"Role: {user_data['role']:12} | Email: {user_data['email']:20} | Senha: {user_data['password']}")
        print("=" * 60)

if __name__ == "__main__":
    create_demo_users()