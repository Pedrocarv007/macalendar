#!/usr/bin/env python
"""
Script para testar atualização de perfil
"""
from app import create_app
from app.extensions.database import db
from app.models.employee import Employee
from datetime import datetime

app = create_app()

with app.app_context():
    # Buscar Pedro Carvalho
    user = Employee.query.filter_by(email='pedrodecarvalho06@gmail.com').first()
    
    if not user:
        print("❌ Usuário Pedro Carvalho não encontrado")
        exit(1)
    
    print(f"✓ Usuário encontrado: {user.name}")
    print(f"  Email: {user.email}")
    print(f"  Role: {user.role}")
    print(f"  Data de Nascimento (antes): {user.birth_date}")
    print(f"  Data de Contratação (antes): {user.hire_date}")
    
    # Testar atualização
    try:
        print("\n📝 Atualizando datas...")
        user.birth_date = datetime.strptime('1990-05-15', '%Y-%m-%d').date()
        user.hire_date = datetime.strptime('2020-01-10', '%Y-%m-%d').date()
        user.updated_at = datetime.utcnow()
        
        db.session.commit()
        print("✓ Datas salvas no banco de dados com sucesso!")
        
        # Verificar
        user_check = Employee.query.filter_by(email='pedrodecarvalho06@gmail.com').first()
        print(f"\n✓ Verificação após salvar:")
        print(f"  Data de Nascimento (depois): {user_check.birth_date}")
        print(f"  Data de Contratação (depois): {user_check.hire_date}")
        
    except Exception as e:
        print(f"❌ Erro ao atualizar: {str(e)}")
        db.session.rollback()
