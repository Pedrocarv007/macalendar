"""Testes para rotas da API de Colaboradores"""
import json
import pytest
from datetime import date


class TestEmployeesGet:
    """Testes para GET /api/employees"""
    
    def test_get_employees_success(self, client, admin_headers, employee_user):
        """Obter lista de colaboradores"""
        response = client.get(
            '/api/employees',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'employees' in data
        assert isinstance(data['employees'], list)
    
    def test_get_employees_unauthenticated(self, client):
        """Obter colaboradores sem autenticação"""
        response = client.get('/api/employees')
        
        assert response.status_code == 401
    
    def test_get_employees_with_filter(self, client, admin_headers, restaurants):
        """Obter colaboradores com filtro de restaurante"""
        response = client.get(
            f'/api/employees?restaurant_id={restaurants["rest1"].id}',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'employees' in data


class TestEmployeesCreate:
    """Testes para POST /api/employees"""
    
    def test_create_employee_success(self, client, admin_headers, restaurants):
        """Criar novo colaborador"""
        response = client.post(
            '/api/employees',
            data=json.dumps({
                'email': 'newemployee@test.com',
                'name': 'New Employee',
                'role': 'employee',
                'department': 'Cozinha',
                'position': 'Chef',
                'birth_date': '1995-06-15',
                'restaurant_id': restaurants['rest1'].id
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code in [200, 201]
        data = json.loads(response.data)
        assert 'id' in data or 'employee' in data
    
    def test_create_employee_duplicate_email(self, client, admin_headers, admin_user, restaurants):
        """Tentar criar colaborador com email duplicado"""
        response = client.post(
            '/api/employees',
            data=json.dumps({
                'email': 'admin@test.com',
                'name': 'Duplicate',
                'role': 'employee',
                'department': 'Cozinha',
                'position': 'Chef',
                'birth_date': '1995-06-15',
                'restaurant_id': restaurants['rest1'].id
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code in [400, 409]
    
    def test_create_employee_invalid_email(self, client, admin_headers, restaurants):
        """Criar colaborador com email inválido"""
        response = client.post(
            '/api/employees',
            data=json.dumps({
                'email': 'invalid-email',
                'name': 'Test',
                'role': 'employee',
                'department': 'Cozinha',
                'position': 'Chef',
                'birth_date': '1995-06-15',
                'restaurant_id': restaurants['rest1'].id
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code in [400, 422]
    
    def test_create_employee_missing_required_fields(self, client, admin_headers, restaurants):
        """Criar colaborador com campos obrigatórios faltando"""
        response = client.post(
            '/api/employees',
            data=json.dumps({
                'email': 'newuser@test.com',
                'name': 'Test'
                # Faltam outros campos
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code in [400, 422]
    
    def test_create_employee_permission_denied(self, client, employee_headers, restaurants):
        """Tentar criar colaborador como employee (sem permissão)"""
        response = client.post(
            '/api/employees',
            data=json.dumps({
                'email': 'newemployee@test.com',
                'name': 'New Employee',
                'role': 'employee',
                'department': 'Cozinha',
                'position': 'Chef',
                'birth_date': '1995-06-15',
                'restaurant_id': restaurants['rest1'].id
            }),
            headers=employee_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 403


class TestEmployeesUpdate:
    """Testes para PUT /api/employees/<id>"""
    
    def test_update_employee_success(self, client, admin_headers, admin_user):
        """Atualizar colaborador"""
        response = client.put(
            f'/api/employees/{admin_user.id}',
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
        assert data['employee']['name'] == 'Updated Name'
    
    def test_update_employee_not_found(self, client, admin_headers):
        """Atualizar colaborador inexistente"""
        response = client.put(
            '/api/employees/99999',
            data=json.dumps({'name': 'Test'}),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 404
    
    def test_update_employee_unauthenticated(self, client, admin_user):
        """Atualizar colaborador sem autenticação"""
        response = client.put(
            f'/api/employees/{admin_user.id}',
            data=json.dumps({'name': 'Test'}),
            content_type='application/json'
        )
        
        assert response.status_code == 401


class TestEmployeesGet:
    """Testes para GET /api/employees/<id>"""
    
    def test_get_employee_success(self, client, admin_headers, admin_user):
        """Obter detalhes de um colaborador"""
        response = client.get(
            f'/api/employees/{admin_user.id}',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['employee']['email'] == admin_user.email
    
    def test_get_employee_not_found(self, client, admin_headers):
        """Obter colaborador inexistente"""
        response = client.get(
            '/api/employees/99999',
            headers=admin_headers
        )
        
        assert response.status_code == 404
    
    def test_get_employee_unauthenticated(self, client, admin_user):
        """Obter colaborador sem autenticação"""
        response = client.get(f'/api/employees/{admin_user.id}')
        
        assert response.status_code == 401


class TestEmployeesDelete:
    """Testes para DELETE /api/employees/<id>"""
    
    def test_delete_employee_success(self, client, app, admin_headers, restaurants):
        """Deletar colaborador"""
        with app.app_context():
            from app.models.employee import Employee
            from app.extensions.database import db
            
            user = Employee(
                email='todelete@test.com',
                name='To Delete',
                role='employee',
                department='Cozinha',
                position='Chef',
                birth_date=date(1995, 6, 15),
                restaurant_id=restaurants['rest1'].id,
                is_active=True
            )
            user.set_password('Password123!')
            db.session.add(user)
            db.session.commit()
            user_id = user.id
        
        response = client.delete(
            f'/api/employees/{user_id}',
            headers=admin_headers
        )
        
        assert response.status_code == 200
    
    def test_delete_employee_not_found(self, client, admin_headers):
        """Deletar colaborador inexistente"""
        response = client.delete(
            '/api/employees/99999',
            headers=admin_headers
        )
        
        assert response.status_code == 404
    
    def test_delete_employee_unauthenticated(self, client, admin_user):
        """Deletar colaborador sem autenticação"""
        response = client.delete(f'/api/employees/{admin_user.id}')
        
        assert response.status_code == 401


class TestEmployeesBirthdays:
    """Testes para endpoints de aniversários"""
    
    def test_get_birthdays_this_month(self, client, admin_headers):
        """Obter aniversários deste mês"""
        response = client.get(
            '/api/employees/birthdays-this-month',
            headers=admin_headers
        )
        
        # Pode retornar lista vazia ou com aniversários
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'birthdays' in data or isinstance(data, list)
    
    def test_get_birthdays_unauthenticated(self, client):
        """Obter aniversários sem autenticação"""
        response = client.get('/api/employees/birthdays-this-month')
        
        assert response.status_code == 401
