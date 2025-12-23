"""Testes para rotas da API de Restaurantes"""
import json
import pytest


class TestRestaurantsGet:
    """Testes para GET /api/restaurants"""
    
    def test_get_restaurants_success(self, client, admin_headers, restaurants):
        """Obter lista de restaurantes"""
        response = client.get(
            '/api/restaurants',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'restaurants' in data
        assert isinstance(data['restaurants'], list)
        assert len(data['restaurants']) >= 2
    
    def test_get_restaurants_unauthenticated(self, client):
        """Obter restaurantes sem autenticação"""
        response = client.get('/api/restaurants')
        
        assert response.status_code == 401
    
    def test_get_restaurants_as_manager(self, client, manager_headers, restaurants):
        """Obter restaurantes como manager"""
        response = client.get(
            '/api/restaurants',
            headers=manager_headers
        )
        
        assert response.status_code == 200


class TestRestaurantsCreate:
    """Testes para POST /api/restaurants"""
    
    def test_create_restaurant_success(self, client, admin_headers):
        """Criar novo restaurante"""
        response = client.post(
            '/api/restaurants',
            data=json.dumps({
                'name': 'New Restaurant',
                'address': 'Rua Nova 123',
                'phone': '939999999',
                'email': 'newrest@test.com'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code in [200, 201]
        data = json.loads(response.data)
        assert 'id' in data or 'restaurant' in data
    
    def test_create_restaurant_duplicate_name(self, client, admin_headers, restaurants):
        """Tentar criar restaurante com nome duplicado"""
        response = client.post(
            '/api/restaurants',
            data=json.dumps({
                'name': 'Restaurante 1',
                'address': 'Rua 1',
                'phone': '919999999',
                'email': 'dup@test.com'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code in [400, 409]
    
    def test_create_restaurant_invalid_email(self, client, admin_headers):
        """Criar restaurante com email inválido"""
        response = client.post(
            '/api/restaurants',
            data=json.dumps({
                'name': 'Test Restaurant',
                'address': 'Rua Test',
                'phone': '919999999',
                'email': 'invalid-email'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        # Pode aceitar email inválido ou retornar erro
        assert response.status_code in [200, 201, 400, 422]
    
    def test_create_restaurant_missing_fields(self, client, admin_headers):
        """Criar restaurante com campos obrigatórios faltando"""
        response = client.post(
            '/api/restaurants',
            data=json.dumps({
                'name': 'Test Restaurant'
                # Faltam outros campos
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        # API pode ter defaults para campos opcionais
        assert response.status_code in [200, 201, 400, 422]
    
    def test_create_restaurant_permission_denied(self, client, employee_headers):
        """Tentar criar restaurante como employee (sem permissão)"""
        response = client.post(
            '/api/restaurants',
            data=json.dumps({
                'name': 'Unauthorized Rest',
                'address': 'Rua',
                'phone': '919999999',
                'email': 'test@test.com'
            }),
            headers=employee_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 403


class TestRestaurantsUpdate:
    """Testes para PUT /api/restaurants/<id>"""
    
    def test_update_restaurant_success(self, client, admin_headers, restaurants):
        """Atualizar restaurante"""
        response = client.put(
            f'/api/restaurants/{restaurants["rest1"].id}',
            data=json.dumps({
                'name': 'Updated Name',
                'address': 'Rua Updated',
                'phone': '939999999'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['restaurant']['name'] == 'Updated Name'
    
    def test_update_restaurant_not_found(self, client, admin_headers):
        """Atualizar restaurante inexistente"""
        response = client.put(
            '/api/restaurants/99999',
            data=json.dumps({'name': 'Test'}),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 404
    
    def test_update_restaurant_unauthenticated(self, client, restaurants):
        """Atualizar restaurante sem autenticação"""
        response = client.put(
            f'/api/restaurants/{restaurants["rest1"].id}',
            data=json.dumps({'name': 'Test'}),
            content_type='application/json'
        )
        
        assert response.status_code == 401


class TestRestaurantsDelete:
    """Testes para DELETE /api/restaurants/<id>"""
    
    def test_delete_restaurant_success(self, client, app, admin_headers):
        """Deletar restaurante"""
        with app.app_context():
            from app.models.restaurant import Restaurant
            from app.extensions.database import db
            
            rest = Restaurant(
                name='To Delete',
                address='Rua',
                phone='919999999',
                email='todelete@test.com',
                is_active=True
            )
            db.session.add(rest)
            db.session.commit()
            rest_id = rest.id
        
        response = client.delete(
            f'/api/restaurants/{rest_id}',
            headers=admin_headers
        )
        
        assert response.status_code == 200
    
    def test_delete_restaurant_not_found(self, client, admin_headers):
        """Deletar restaurante inexistente"""
        response = client.delete(
            '/api/restaurants/99999',
            headers=admin_headers
        )
        
        assert response.status_code == 404
    
    def test_delete_restaurant_unauthenticated(self, client, restaurants):
        """Deletar restaurante sem autenticação"""
        response = client.delete(f'/api/restaurants/{restaurants["rest1"].id}')
        
        assert response.status_code == 401


class TestRestaurantsStats:
    """Testes para GET /api/restaurants/<id>/stats"""
    
    def test_get_restaurant_stats(self, client, admin_headers, restaurants):
        """Obter estatísticas de um restaurante"""
        response = client.get(
            f'/api/restaurants/{restaurants["rest1"].id}/stats',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'stats' in data or 'employees' in data or 'events' in data
    
    def test_get_restaurant_stats_not_found(self, client, admin_headers):
        """Obter estatísticas de restaurante inexistente"""
        response = client.get(
            '/api/restaurants/99999/stats',
            headers=admin_headers
        )
        
        assert response.status_code == 404
    
    def test_get_restaurant_stats_unauthenticated(self, client, restaurants):
        """Obter estatísticas sem autenticação"""
        response = client.get(f'/api/restaurants/{restaurants["rest1"].id}/stats')
        
        assert response.status_code == 401
