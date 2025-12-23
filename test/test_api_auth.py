"""Testes para rotas da API de autenticação"""
import json
import pytest


class TestAuthLogin:
    """Testes do endpoint /api/auth/login"""
    
    def test_login_success_admin(self, client, admin_user):
        """Login bem-sucedido com admin"""
        response = client.post(
            '/api/auth/login',
            data=json.dumps({
                'email': 'admin@test.com',
                'password': 'Admin123!'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data
        assert data['user']['email'] == 'admin@test.com'
        assert data['user']['role'] == 'admin'
    
    def test_login_invalid_email_format(self, client):
        """Login com formato de email inválido"""
        response = client.post(
            '/api/auth/login',
            data=json.dumps({
                'email': 'invalid-email',
                'password': 'Password123!'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_login_wrong_password(self, client, admin_user):
        """Login com senha incorreta"""
        response = client.post(
            '/api/auth/login',
            data=json.dumps({
                'email': 'admin@test.com',
                'password': 'WrongPassword123!'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 401
    
    def test_login_non_existent_user(self, client):
        """Login com usuário que não existe"""
        response = client.post(
            '/api/auth/login',
            data=json.dumps({
                'email': 'nonexistent@test.com',
                'password': 'Password123!'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 401
    
    def test_login_missing_email(self, client):
        """Login sem email"""
        response = client.post(
            '/api/auth/login',
            data=json.dumps({
                'password': 'Password123!'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_login_missing_password(self, client):
        """Login sem senha"""
        response = client.post(
            '/api/auth/login',
            data=json.dumps({
                'email': 'admin@test.com'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_login_empty_body(self, client):
        """Login com body vazio"""
        response = client.post(
            '/api/auth/login',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        assert response.status_code == 400


class TestAuthProfile:
    """Testes para endpoints de perfil"""
    
    def test_get_profile_authenticated(self, client, admin_user, admin_headers):
        """Obter perfil com autenticação"""
        response = client.get(
            '/api/auth/profile',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user']['email'] == 'admin@test.com'
    
    def test_get_profile_unauthenticated(self, client):
        """Obter perfil sem autenticação"""
        response = client.get('/api/auth/profile')
        
        assert response.status_code == 401
    
    def test_update_profile_success(self, client, admin_user, admin_headers):
        """Atualizar perfil com sucesso"""
        response = client.put(
            '/api/auth/profile',
            data=json.dumps({
                'name': 'Admin Updated',
                'department': 'IT',
                'position': 'Tech Lead'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user']['name'] == 'Admin Updated'
    
    def test_update_profile_unauthenticated(self, client):
        """Atualizar perfil sem autenticação"""
        response = client.put(
            '/api/auth/profile',
            data=json.dumps({'name': 'New Name'}),
            content_type='application/json'
        )
        
        assert response.status_code == 401


class TestAuthChangePassword:
    """Testes para mudança de senha"""
    
    def test_change_password_success(self, client, admin_user, admin_headers):
        """Mudar senha com sucesso"""
        response = client.post(
            '/api/auth/change-password',
            data=json.dumps({
                'current_password': 'Admin123!',
                'new_password': 'NewPassword123!'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 200
    
    def test_change_password_wrong_current(self, client, admin_user, admin_headers):
        """Mudar senha com senha atual incorreta"""
        response = client.post(
            '/api/auth/change-password',
            data=json.dumps({
                'current_password': 'WrongPassword123!',
                'new_password': 'NewPassword123!'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 400 or response.status_code == 401
    
    def test_change_password_unauthenticated(self, client):
        """Mudar senha sem autenticação"""
        response = client.post(
            '/api/auth/change-password',
            data=json.dumps({
                'current_password': 'Admin123!',
                'new_password': 'NewPassword123!'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 401


class TestAuthMe:
    """Testes para endpoints /me"""
    
    def test_get_current_user(self, client, admin_headers):
        """Obter usuário atual"""
        response = client.get(
            '/api/auth/me',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'user' in data or 'id' in data
    
    def test_get_current_user_info(self, client, admin_headers):
        """Obter informações do usuário atual"""
        response = client.get(
            '/api/auth/current-user',
            headers=admin_headers
        )
        
        assert response.status_code == 200


class TestAuthUsers:
    """Testes para listar usuários"""
    
    def test_list_users_admin(self, client, admin_user, admin_headers):
        """Listar usuários como admin"""
        response = client.get(
            '/api/auth/users',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'users' in data or isinstance(data, list)
    
    def test_list_users_unauthenticated(self, client):
        """Listar usuários sem autenticação"""
        response = client.get('/api/auth/users')
        
        assert response.status_code == 401
