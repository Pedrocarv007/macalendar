"""Testes para rotas da API de Perfil e Dashboard"""
import json
import pytest


class TestProfileMe:
    """Testes para GET/PUT /api/profile/me"""
    
    def test_get_profile_success(self, client, admin_headers):
        """Obter perfil do usuário"""
        response = client.get(
            '/api/profile/me',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'name' in data or 'user' in data
    
    def test_get_profile_unauthenticated(self, client):
        """Obter perfil sem autenticação"""
        response = client.get('/api/profile/me')
        
        assert response.status_code == 401
    
    def test_update_profile_success(self, client, admin_headers):
        """Atualizar perfil"""
        response = client.put(
            '/api/profile/me',
            data=json.dumps({
                'name': 'Updated Name',
                'department': 'RH',
                'position': 'Director'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        # API returns 'message' and 'user' fields
        assert 'message' in data or 'user' in data
    
    def test_update_profile_unauthenticated(self, client):
        """Atualizar perfil sem autenticação"""
        response = client.put(
            '/api/profile/me',
            data=json.dumps({'name': 'Test'}),
            content_type='application/json'
        )
        
        assert response.status_code == 401


class TestProfilePassword:
    """Testes para POST /api/profile/me/password"""
    
    def test_change_password_success(self, client, admin_headers):
        """Mudar senha com sucesso"""
        response = client.post(
            '/api/profile/me/password',
            data=json.dumps({
                'current_password': 'Admin123!',
                'new_password': 'NewPassword123!'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 200
    
    def test_change_password_wrong_current(self, client, admin_headers):
        """Mudar senha com senha atual incorreta"""
        response = client.post(
            '/api/profile/me/password',
            data=json.dumps({
                'current_password': 'WrongPassword!',
                'new_password': 'NewPassword123!'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code in [400, 401]
    
    def test_change_password_missing_fields(self, client, admin_headers):
        """Mudar senha com campos faltando"""
        response = client.post(
            '/api/profile/me/password',
            data=json.dumps({
                'current_password': 'Admin123!'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code in [400, 422]
    
    def test_change_password_unauthenticated(self, client):
        """Mudar senha sem autenticação"""
        response = client.post(
            '/api/profile/me/password',
            data=json.dumps({
                'current_password': 'Admin123!',
                'new_password': 'NewPassword123!'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 401


class TestDashboardStats:
    """Testes para GET /api/dashboard/stats"""
    
    def test_get_stats_success(self, client, admin_headers):
        """Obter estatísticas do dashboard"""
        response = client.get(
            '/api/dashboard/stats',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        # Pode conter diferentes campos dependendo da implementação
        assert isinstance(data, dict)
    
    def test_get_stats_unauthenticated(self, client):
        """Obter estatísticas sem autenticação"""
        response = client.get('/api/dashboard/stats')
        
        assert response.status_code == 401


class TestDashboardRecentEvents:
    """Testes para GET /api/dashboard/events/recent"""
    
    def test_get_recent_events_success(self, client, admin_headers):
        """Obter eventos recentes"""
        response = client.get(
            '/api/dashboard/events/recent',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'events' in data or isinstance(data, list)
    
    def test_get_recent_events_unauthenticated(self, client):
        """Obter eventos recentes sem autenticação"""
        response = client.get('/api/dashboard/events/recent')
        
        assert response.status_code == 401
    
    def test_get_recent_events_with_limit(self, client, admin_headers):
        """Obter eventos recentes com limite"""
        response = client.get(
            '/api/dashboard/events/recent?limit=5',
            headers=admin_headers
        )
        
        assert response.status_code == 200


class TestDashboardActivities:
    """Testes para GET /api/dashboard/activities"""
    
    def test_get_activities_success(self, client, admin_headers):
        """Obter atividades recentes"""
        response = client.get(
            '/api/dashboard/activities',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'activities' in data or isinstance(data, list)
    
    def test_get_activities_unauthenticated(self, client):
        """Obter atividades sem autenticação"""
        response = client.get('/api/dashboard/activities')
        
        assert response.status_code == 401
    
    def test_get_activities_with_limit(self, client, admin_headers):
        """Obter atividades com limite"""
        response = client.get(
            '/api/dashboard/activities?limit=10',
            headers=admin_headers
        )
        
        assert response.status_code == 200


class TestWebDashboard:
    """Testes para páginas web do dashboard"""
    
    def test_dashboard_redirect_unauthenticated(self, client):
        """Acessar dashboard sem autenticação redireciona para login"""
        response = client.get('/dashboard', follow_redirects=False)
        
        assert response.status_code in [302, 401]
    
    def test_index_redirect(self, client):
        """Página raiz redireciona corretamente"""
        response = client.get('/', follow_redirects=False)
        
        assert response.status_code in [200, 302, 401]
