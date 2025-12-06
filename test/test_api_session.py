#!/usr/bin/env python
"""
Script para testar a API de profile e verificar o middleware
"""
import requests
import json
from app import create_app
from app.extensions.database import db
from app.models.employee import Employee

app = create_app()

# Primeiro, fazer login para obter sessão
with app.test_client() as client:
    # Fazer login
    print("🔐 Fazendo login como Pedro Carvalho...")
    login_response = client.post('/auth/login', data={
        'email': 'pedrodecarvalho06@gmail.com',
        'password': 'Pedro@123456',
        'remember': 'no'
    }, follow_redirects=False)
    
    print(f"Status do login: {login_response.status_code}")
    print(f"Content-Type: {login_response.content_type}")
    print(f"Resposta: {login_response.data[:200]}")
    
    # Obter a sessão
    with client.session_transaction() as sess:
        print(f"\n📋 Sessão depois do login:")
        print(f"  user_id: {sess.get('user_id')}")
        print(f"  user_role: {sess.get('user_role')}")
        print(f"  user_name: {sess.get('user_name')}")
        print(f"  restaurant_id: {sess.get('restaurant_id')}")
    
    # Agora fazer uma requisição GET para /api/profile/me
    print("\n\n📡 Testando GET /api/profile/me...")
    profile_response = client.get('/api/profile/me')
    print(f"Status: {profile_response.status_code}")
    if profile_response.status_code == 200:
        data = profile_response.get_json()
        print(f"✓ Perfil carregado com sucesso")
        print(f"  Name: {data.get('name')}")
        print(f"  Email: {data.get('email')}")
        print(f"  Role: {data.get('role')}")
        print(f"  Birth date: {data.get('birth_date')}")
        print(f"  Hire date: {data.get('hire_date')}")
    else:
        print(f"❌ Erro: {profile_response.get_json()}")
    
    # Testar atualização de datas
    print("\n\n✏️  Testando PUT /api/profile/me com novas datas...")
    update_data = {
        'name': 'Pedro Carvalho',
        'phone': '11999999999',
        'birthDate': '1990-06-20',
        'hireDate': '2020-02-15',
        'position': 'Desenvolvedor',
        'department': 'Desenvolvedor',
        'address': 'Rua Teste, 123',
        'notes': 'Teste de atualização'
    }
    
    update_response = client.put(
        '/api/profile/me',
        data=json.dumps(update_data),
        content_type='application/json'
    )
    
    print(f"Status: {update_response.status_code}")
    if update_response.status_code == 200:
        result = update_response.get_json()
        print(f"✓ Atualização bem-sucedida!")
        user_data = result.get('user', {})
        print(f"  Name: {user_data.get('name')}")
        print(f"  Birth date: {user_data.get('birth_date')}")
        print(f"  Hire date: {user_data.get('hire_date')}")
    else:
        print(f"❌ Erro: {update_response.get_json()}")
    
    # Verificar no banco de dados
    print("\n\n🔍 Verificando no banco de dados...")
    with app.app_context():
        user = Employee.query.filter_by(email='pedrodecarvalho06@gmail.com').first()
        if user:
            print(f"✓ Usuário encontrado")
            print(f"  Birth date no DB: {user.birth_date}")
            print(f"  Hire date no DB: {user.hire_date}")
