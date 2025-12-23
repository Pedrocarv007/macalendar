"""Configuração compartilhada para todos os testes"""
import json
import os
from datetime import date
import pytest

from app import create_app
from app.extensions.database import db
from app.models.employee import Employee
from app.models.restaurant import Restaurant
from app.models.calendar_event import CalendarEvent
from app.models.document import Document


@pytest.fixture
def app():
    """Criar aplicação para testes"""
    # Definir config antes de criar app
    os.environ['FLASK_CONFIG'] = 'testing'
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-jwt'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_ECHO'] = False
    app.config['APPLICATION_ROOT'] = '/'  # Necessário para testes
    app.config['JWT_SECRET_KEY'] = 'test-secret-key-for-jwt'
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture  
def client(app):
    """Cliente de teste"""
    return app.test_client()


@pytest.fixture
def restaurants(app):
    """Criar restaurantes para testes"""
    with app.app_context():
        rest1 = Restaurant(
            name='Restaurante 1',
            address='Rua 1',
            phone='919999999',
            email='rest1@test.com',
            is_active=True
        )
        rest2 = Restaurant(
            name='Restaurante 2',
            address='Rua 2',
            phone='929999999',
            email='rest2@test.com',
            is_active=True
        )
        db.session.add(rest1)
        db.session.add(rest2)
        db.session.commit()
        rest1_id = rest1.id
        rest2_id = rest2.id
    
    with app.app_context():
        return {
            'rest1': Restaurant.query.get(rest1_id),
            'rest2': Restaurant.query.get(rest2_id)
        }


@pytest.fixture
def admin_user(client, restaurants):
    """Criar usuário admin"""
    with client.application.app_context():
        user = Employee(
            email='admin@test.com',
            name='Admin User',
            role='admin',
            department='TI',
            position='Administrador',
            birth_date=date(1990, 1, 1),
            restaurant_id=restaurants['rest1'].id,
            is_active=True
        )
        user.set_password('Admin123!')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    
    with client.application.app_context():
        return Employee.query.get(user_id)


@pytest.fixture
def manager_user(client, restaurants):
    """Criar usuário manager"""
    with client.application.app_context():
        user = Employee(
            email='manager@test.com',
            name='Manager User',
            role='manager',
            department='RH',
            position='Gerente',
            birth_date=date(1992, 5, 15),
            restaurant_id=restaurants['rest1'].id,
            is_active=True
        )
        user.set_password('Manager123!')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    
    with client.application.app_context():
        return Employee.query.get(user_id)


@pytest.fixture
def employee_user(client, restaurants):
    """Criar usuário employee"""
    with client.application.app_context():
        user = Employee(
            email='employee@test.com',
            name='Employee User',
            role='employee',
            department='Cozinha',
            position='Cozinheiro',
            birth_date=date(1995, 10, 20),
            restaurant_id=restaurants['rest1'].id,
            is_active=True
        )
        user.set_password('Employee123!')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    
    with client.application.app_context():
        return Employee.query.get(user_id)


@pytest.fixture
def admin_token(client, admin_user):
    """Token de autenticação admin"""
    response = client.post(
        '/api/auth/login',
        data=json.dumps({
            'email': 'admin@test.com',
            'password': 'Admin123!'
        }),
        content_type='application/json'
    )
    data = json.loads(response.data)
    return data.get('access_token')


@pytest.fixture
def manager_token(client, manager_user):
    """Token de autenticação manager"""
    response = client.post(
        '/api/auth/login',
        data=json.dumps({
            'email': 'manager@test.com',
            'password': 'Manager123!'
        }),
        content_type='application/json'
    )
    data = json.loads(response.data)
    return data.get('access_token')


@pytest.fixture
def employee_token(client, employee_user):
    """Token de autenticação employee"""
    response = client.post(
        '/api/auth/login',
        data=json.dumps({
            'email': 'employee@test.com',
            'password': 'Employee123!'
        }),
        content_type='application/json'
    )
    data = json.loads(response.data)
    return data.get('access_token')


@pytest.fixture
def admin_headers(admin_token):
    """Headers com token admin"""
    return {'Authorization': f'Bearer {admin_token}'}


@pytest.fixture
def manager_headers(manager_token):
    """Headers com token manager"""
    return {'Authorization': f'Bearer {manager_token}'}


@pytest.fixture
def employee_headers(employee_token):
    """Headers com token employee"""
    return {'Authorization': f'Bearer {employee_token}'}
