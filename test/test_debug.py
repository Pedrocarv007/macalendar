#!/usr/bin/env python
"""Script de debug para testes"""
import os
import json
import traceback
os.environ['FLASK_CONFIG'] = 'testing'

from app import create_app
from app.extensions.database import db
from app.models.restaurant import Restaurant
from app.models.employee import Employee
from datetime import date

app = create_app('testing')
app.config['TESTING'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['WTF_CSRF_ENABLED'] = False
app.config['APPLICATION_ROOT'] = '/'
app.config['DEBUG'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True

with app.app_context():
    db.create_all()
    
    # Criar restaurante
    rest = Restaurant(
        name='Test Rest',
        address='Rua',
        phone='919999999',
        email='rest@test.com',
        is_active=True
    )
    db.session.add(rest)
    db.session.commit()
    
    # Criar user
    user = Employee(
        email='admin@test.com',
        name='Admin',
        role='admin',
        department='TI',
        position='Admin',
        birth_date=date(1990, 1, 1),
        restaurant_id=rest.id,
        is_active=True
    )
    user.set_password('Admin123!')
    db.session.add(user)
    db.session.commit()
    
    # Testar login
    client = app.test_client()
    try:
        response = client.post(
            '/api/auth/login',
            data=json.dumps({'email': 'admin@test.com', 'password': 'Admin123!'}),
            content_type='application/json'
        )
        
        print(f'Status: {response.status_code}')
        print(f'Response: {response.data.decode("utf-8", errors="replace")}')
        
        if response.status_code != 200:
            print(f'\nError: Expected 200, got {response.status_code}')
        else:
            data = json.loads(response.data)
            print(f'\nSucesso! Token obtido: {data["access_token"][:20]}...')
    except Exception as e:
        print(f'Exception: {e}')
        traceback.print_exc()
