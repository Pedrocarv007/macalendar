"""
Script de configuração inicial do banco de dados
"""
import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para importar a aplicação
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.extensions.database import db
from app.models.user import User
from app.models.restaurant import Restaurant
from app.models.employee import Employee
from datetime import date

def create_sample_data():
    """Criar dados de exemplo"""
    
    print("Criando dados de exemplo...")
    
    # Criar restaurante de exemplo
    restaurant = Restaurant(
        name="MAC Central",
        address="Rua Principal, 123 - Centro",
        phone="(11) 99999-9999",
        email="central@mac.com"
    )
    db.session.add(restaurant)
    db.session.commit()
    
    # Criar usuário admin
    admin = User(
        email="admin@mac.com",
        name="Administrador",
        role="admin",
        department="TI"
    )
    admin.set_password("admin123")
    db.session.add(admin)
    
    # Criar usuário RH
    rh_user = User(
        email="rh@mac.com",
        name="Recursos Humanos", 
        role="rh",
        department="RH",
        restaurant_id=restaurant.id
    )
    rh_user.set_password("rh123")
    db.session.add(rh_user)
    
    # Criar gerente
    manager = User(
        email="gerente@mac.com",
        name="João Gerente",
        role="manager",
        department="Gerência",
        restaurant_id=restaurant.id
    )
    manager.set_password("gerente123")
    db.session.add(manager)
    
    db.session.commit()
    
    # Definir gerente do restaurante
    restaurant.manager_id = manager.id
    db.session.commit()
    
    # Criar funcionários de exemplo
    employees = [
        {
            "name": "Maria Silva",
            "email": "maria@mac.com",
            "position": "Garçonete",
            "birth_date": date(1990, 3, 15),
            "hire_date": date(2020, 1, 10)
        },
        {
            "name": "Carlos Santos",
            "email": "carlos@mac.com", 
            "position": "Cozinheiro",
            "birth_date": date(1985, 7, 22),
            "hire_date": date(2019, 5, 20)
        },
        {
            "name": "Ana Costa",
            "email": "ana@mac.com",
            "position": "Caixa",
            "birth_date": date(1992, 11, 8),
            "hire_date": date(2021, 3, 1)
        }
    ]
    
    for emp_data in employees:
        employee = Employee(
            name=emp_data["name"],
            email=emp_data["email"],
            position=emp_data["position"],
            birth_date=emp_data["birth_date"],
            hire_date=emp_data["hire_date"],
            restaurant_id=restaurant.id
        )
        db.session.add(employee)
    
    db.session.commit()
    
    print("✅ Dados de exemplo criados com sucesso!")
    print("\n👤 Usuários criados:")
    print("- Admin: admin@mac.com / admin123")
    print("- RH: rh@mac.com / rh123") 
    print("- Gerente: gerente@mac.com / gerente123")
    print(f"\n🏢 Restaurante: {restaurant.name}")
    print(f"👥 Funcionários: {len(employees)} colaboradores")

def setup_database():
    """Configurar banco de dados"""
    
    print("🚀 Configurando banco de dados...")
    
    # Criar aplicação
    app = create_app()
    
    with app.app_context():
        # Criar todas as tabelas
        print("📝 Criando tabelas...")
        db.create_all()
        
        # Verificar se já existem dados
        if User.query.first():
            print("⚠️  Banco de dados já contém dados.")
            response = input("Deseja recriar os dados de exemplo? (s/N): ")
            if response.lower() != 's':
                print("❌ Operação cancelada.")
                return
            
            # Limpar dados existentes
            print("🗑️  Removendo dados existentes...")
            db.drop_all()
            db.create_all()
        
        # Criar dados de exemplo
        create_sample_data()
        
        print("✅ Configuração concluída!")

if __name__ == "__main__":
    setup_database()