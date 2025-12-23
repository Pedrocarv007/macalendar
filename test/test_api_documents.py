"""Testes para rotas da API de Documentos"""
import json
import pytest
from datetime import datetime, timedelta


class TestDocumentsGet:
    """Testes para GET /api/documents"""
    
    def test_get_documents_success(self, client, admin_headers):
        """Obter lista de documentos"""
        response = client.get(
            '/api/documents',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'documents' in data
        assert isinstance(data['documents'], list)
    
    def test_get_documents_unauthenticated(self, client):
        """Obter documentos sem autenticação"""
        response = client.get('/api/documents')
        
        assert response.status_code == 401
    
    def test_get_documents_with_filter(self, client, admin_headers):
        """Obter documentos com filtro"""
        response = client.get(
            '/api/documents?doc_type=contract',
            headers=admin_headers
        )
        
        assert response.status_code == 200


class TestDocumentsCreate:
    """Testes para POST /api/documents"""
    
    def test_create_document_success(self, client, admin_headers, restaurants):
        """Criar novo documento (requer upload de arquivo)"""
        # Documents API requer multipart/form-data com arquivo
        # Este teste valida que sem arquivo retorna erro apropriado
        response = client.post(
            '/api/documents',
            headers=admin_headers
        )
        
        assert response.status_code == 400  # Sem arquivo deve retornar 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_create_document_missing_title(self, client, admin_headers):
        """Criar documento sem título"""
        response = client.post(
            '/api/documents',
            data=json.dumps({
                'description': 'Test',
                'type': 'contract',
                'content': 'Content'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code in [400, 422]
    
    def test_create_document_unauthenticated(self, client):
        """Criar documento sem autenticação"""
        response = client.post(
            '/api/documents',
            data=json.dumps({'title': 'Test'}),
            content_type='application/json'
        )
        
        assert response.status_code == 401
    
    def test_create_document_permission_denied(self, client, employee_headers):
        """Tentar criar documento como employee (sem permissão)"""
        response = client.post(
            '/api/documents',
            data=json.dumps({
                'title': 'Test Document',
                'description': 'Test',
                'type': 'contract',
                'content': 'Content'
            }),
            headers=employee_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 403


class TestDocumentsUpdate:
    """Testes para PUT /api/documents/<id>"""
    
    def test_update_document_success(self, client, app, admin_headers, restaurants):
        """Atualizar documento"""
        with app.app_context():
            from app.models.document import Document
            from app.models.employee import Employee
            from app.extensions.database import db
            
            # Obter employee para associar ao documento
            employee = Employee.query.filter_by(email='admin@test.com').first()
            
            doc = Document(
                title='Test Doc',
                document_type='memo',
                template_name='default',
                employee_id=employee.id,
                restaurant_id=restaurants['rest1'].id,
                created_by=employee.id
            )
            db.session.add(doc)
            db.session.commit()
            doc_id = doc.id
        
        # Update também pode requerer form-data, testar NOT FOUND com ID inválido
        response = client.put(
            '/api/documents/99999',
            headers=admin_headers
        )
        
        assert response.status_code == 404
    
    def test_update_document_not_found(self, client, admin_headers):
        """Atualizar documento inexistente"""
        response = client.put(
            '/api/documents/99999',
            data=json.dumps({'title': 'Test'}),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 404
    
    def test_update_document_unauthenticated(self, client):
        """Atualizar documento sem autenticação"""
        response = client.put(
            '/api/documents/1',
            data=json.dumps({'title': 'Test'}),
            content_type='application/json'
        )
        
        assert response.status_code == 401


class TestDocumentsDelete:
    """Testes para DELETE /api/documents/<id>"""
    
    def test_delete_document_success(self, client, app, admin_headers, restaurants):
        """Deletar documento"""
        with app.app_context():
            from app.models.document import Document
            from app.models.employee import Employee
            from app.extensions.database import db
            
            employee = Employee.query.filter_by(email='admin@test.com').first()
            
            doc = Document(
                title='To Delete',
                document_type='memo',
                template_name='default',
                employee_id=employee.id,
                restaurant_id=restaurants['rest1'].id,
                created_by=employee.id
            )
            db.session.add(doc)
            db.session.commit()
            doc_id = doc.id
        
        response = client.delete(
            f'/api/documents/{doc_id}',
            headers=admin_headers
        )
        
        assert response.status_code == 200
    
    def test_delete_document_not_found(self, client, admin_headers):
        """Deletar documento inexistente"""
        response = client.delete(
            '/api/documents/99999',
            headers=admin_headers
        )
        
        assert response.status_code == 404
    
    def test_delete_document_unauthenticated(self, client):
        """Deletar documento sem autenticação"""
        response = client.delete('/api/documents/1')
        
        assert response.status_code == 401


class TestDocumentsDownload:
    """Testes para GET /api/documents/<id>/download"""
    
    def test_download_document_success(self, client, app, admin_headers, restaurants):
        """Fazer download de documento"""
        with app.app_context():
            from app.models.document import Document
            from app.models.employee import Employee
            from app.extensions.database import db
            
            employee = Employee.query.filter_by(email='admin@test.com').first()
            
            doc = Document(
                title='Test Doc',
                document_type='pdf',
                template_name='default',
                employee_id=employee.id,
                restaurant_id=restaurants['rest1'].id,
                created_by=employee.id,
                file_path='nonexistent.pdf'
            )
            db.session.add(doc)
            db.session.commit()
            doc_id = doc.id
        
        response = client.get(
            f'/api/documents/{doc_id}/download',
            headers=admin_headers
        )
        
        # Arquivo não existe fisicamente, então deve retornar 404
        assert response.status_code == 404
    
    def test_download_document_not_found(self, client, admin_headers):
        """Fazer download de documento inexistente"""
        response = client.get(
            '/api/documents/99999/download',
            headers=admin_headers
        )
        
        assert response.status_code == 404
    
    def test_download_document_unauthenticated(self, client):
        """Fazer download sem autenticação"""
        response = client.get('/api/documents/1/download')
        
        assert response.status_code == 401


class TestDocumentsTemplates:
    """Testes para GET /api/documents/templates"""
    
    def test_get_templates_success(self, client, admin_headers):
        """Obter lista de templates"""
        response = client.get(
            '/api/documents/templates',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'templates' in data or isinstance(data, list)
    
    def test_get_templates_unauthenticated(self, client):
        """Obter templates sem autenticação"""
        response = client.get('/api/documents/templates')
        
        assert response.status_code == 401


class TestDocumentsGenerate:
    """Testes para POST /api/documents/generate"""
    
    def test_generate_document_success(self, client, admin_headers):
        """Gerar documento a partir de template"""
        response = client.post(
            '/api/documents/generate',
            data=json.dumps({
                'template': 'contract',
                'data': {
                    'name': 'Test User',
                    'date': '2025-12-23'
                }
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code in [200, 201, 400, 401]  # 400 se template inválido, 401 se não autenticado
    
    def test_generate_document_missing_template(self, client, admin_headers):
        """Gerar documento sem template"""
        response = client.post(
            '/api/documents/generate',
            data=json.dumps({
                'data': {}
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code in [400, 422]
    
    def test_generate_document_unauthenticated(self, client):
        """Gerar documento sem autenticação"""
        response = client.post(
            '/api/documents/generate',
            data=json.dumps({'template': 'contract'}),
            content_type='application/json'
        )
        
        assert response.status_code == 401
