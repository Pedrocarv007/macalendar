"""Testes de autenticação para endpoints da API."""
import json
from datetime import date

import pytest

from app import create_app
from app.extensions.database import db
from app.models.employee import Employee
from app.models.restaurant import Restaurant

@pytest.fixture
def app():
    """Criar aplicação para testes"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()

        restaurant = Restaurant(
            name='Restaurante Teste',
            address='Rua 123',
            phone='999999999',
            email='restaurante@test.com',
            is_active=True
        )
        db.session.add(restaurant)
        db.session.commit()

        user = Employee(
            email='test@mac.com',
            name='Test User',
            role='admin',
            department='TI',
            position='Administrador',
            birth_date=date(1990, 1, 1),
            restaurant_id=restaurant.id,
            is_active=True
        )
        user.set_password('test123A!')
        db.session.add(user)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

@pytest.fixture  
def client(app):
    """Cliente de teste"""
    return app.test_client()

@pytest.fixture
def auth_headers(client):
    """Headers com token de autenticação"""
    response = client.post('/api/auth/login',
        data=json.dumps({
            'email': 'test@mac.com',
            'password': 'test123A!'
        }),
        content_type='application/json'
    )
    
    data = json.loads(response.data)
    token = data['access_token']
    
    return {'Authorization': f'Bearer {token}'}

class TestAuth:
    """Testes de autenticação"""
    
    def test_login_success(self, client):
        """Teste de login com sucesso"""
        response = client.post(
            '/api/auth/login',
            data=json.dumps({
                'email': 'test@mac.com',
                'password': 'test123A!'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data
        assert data['user']['email'] == 'test@mac.com'
    
    def test_login_invalid_credentials(self, client):
        """Teste de login com credenciais inválidas"""
        response = client.post('/api/auth/login',
            data=json.dumps({
                'email': 'test@mac.com',
                'password': 'wrong_password'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_login_missing_data(self, client):
        """Teste de login sem dados"""
        response = client.post('/api/auth/login',
            data=json.dumps({
                'email': 'test@mac.com'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_get_profile(self, client, auth_headers):
        """Teste de obter perfil"""
        response = client.get('/api/auth/profile', 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user']['email'] == 'test@mac.com'
    
    def test_get_profile_without_auth(self, client):
        """Teste de obter perfil sem autenticação"""
        response = client.get('/api/auth/profile')
        
        assert response.status_code == 401