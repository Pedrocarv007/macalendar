"""Testes para rotas da API de Calendário"""
import json
import pytest
from datetime import datetime, timedelta


class TestCalendarEventsGet:
    """Testes para GET /api/calendar/events"""
    
    def test_get_events_success(self, client, admin_headers):
        """Obter lista de eventos"""
        response = client.get(
            '/api/calendar/events',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'events' in data
        assert isinstance(data['events'], list)
    
    def test_get_events_unauthenticated(self, client):
        """Obter eventos sem autenticação"""
        response = client.get('/api/calendar/events')
        
        assert response.status_code == 401
    
    def test_get_events_with_date_filter(self, client, admin_headers):
        """Obter eventos com filtro de data"""
        today = datetime.utcnow().date()
        response = client.get(
            f'/api/calendar/events?start_date={today}&end_date={today}',
            headers=admin_headers
        )
        
        assert response.status_code == 200


class TestCalendarEventsCreate:
    """Testes para POST /api/calendar/events"""
    
    def test_create_event_success(self, client, admin_headers):
        """Criar novo evento"""
        start_date = (datetime.utcnow() + timedelta(days=1)).isoformat()
        end_date = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat()
        
        response = client.post(
            '/api/calendar/events',
            data=json.dumps({
                'title': 'Test Event',
                'description': 'Test Description',
                'start_date': start_date,
                'end_date': end_date,
                'event_type': 'meeting'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code in [200, 201]
        data = json.loads(response.data)
        assert 'id' in data or 'event' in data
    
    def test_create_event_missing_title(self, client, admin_headers):
        """Criar evento sem título"""
        start_date = (datetime.utcnow() + timedelta(days=1)).isoformat()
        end_date = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat()
        
        response = client.post(
            '/api/calendar/events',
            data=json.dumps({
                'description': 'Test',
                'start_date': start_date,
                'end_date': end_date,
                'event_type': 'meeting'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code in [400, 422]
    
    def test_create_event_invalid_date(self, client, admin_headers):
        """Criar evento com data inválida"""
        response = client.post(
            '/api/calendar/events',
            data=json.dumps({
                'title': 'Test',
                'start_date': 'invalid-date',
                'end_date': 'invalid-date'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code in [400, 422]
    
    def test_create_event_unauthenticated(self, client):
        """Criar evento sem autenticação"""
        response = client.post(
            '/api/calendar/events',
            data=json.dumps({'title': 'Test'}),
            content_type='application/json'
        )
        
        assert response.status_code == 401


class TestCalendarEventsUpdate:
    """Testes para PUT /api/calendar/events/<id>"""
    
    def test_update_event_success(self, client, app, admin_headers):
        """Atualizar evento"""
        with app.app_context():
            from app.models.calendar_event import CalendarEvent
            from app.models.employee import Employee
            from app.extensions.database import db
            
            # Obter employee para created_by
            employee = Employee.query.filter_by(email='admin@test.com').first()
            
            event = CalendarEvent(
                title='Test Event',
                description='Test',
                start_date=datetime.utcnow() + timedelta(days=1),
                end_date=datetime.utcnow() + timedelta(days=1, hours=2),
                event_type='meeting',
                created_by=employee.id
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id
        
        response = client.put(
            f'/api/calendar/events/{event_id}',
            data=json.dumps({
                'title': 'Updated Event'
            }),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['event']['title'] == 'Updated Event'
    
    def test_update_event_not_found(self, client, admin_headers):
        """Atualizar evento inexistente"""
        response = client.put(
            '/api/calendar/events/99999',
            data=json.dumps({'title': 'Test'}),
            headers=admin_headers,
            content_type='application/json'
        )
        
        assert response.status_code == 404
    
    def test_update_event_unauthenticated(self, client):
        """Atualizar evento sem autenticação"""
        response = client.put(
            '/api/calendar/events/1',
            data=json.dumps({'title': 'Test'}),
            content_type='application/json'
        )
        
        assert response.status_code == 401


class TestCalendarEventsDelete:
    """Testes para DELETE /api/calendar/events/<id>"""
    
    def test_delete_event_success(self, client, app, admin_user, admin_headers):
        """Deletar evento"""
        with app.app_context():
            from app.models.calendar_event import CalendarEvent
            from app.extensions.database import db
            
            event = CalendarEvent(
                title='To Delete',
                description='Test',
                start_date=datetime.utcnow() + timedelta(days=1),
                end_date=datetime.utcnow() + timedelta(days=1, hours=2),
                event_type='meeting',
                created_by=admin_user.id
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id
        
        response = client.delete(
            f'/api/calendar/events/{event_id}',
            headers=admin_headers
        )
        
        assert response.status_code == 200
    
    def test_delete_event_not_found(self, client, admin_headers):
        """Deletar evento inexistente"""
        response = client.delete(
            '/api/calendar/events/99999',
            headers=admin_headers
        )
        
        assert response.status_code == 404
    
    def test_delete_event_unauthenticated(self, client):
        """Deletar evento sem autenticação"""
        response = client.delete('/api/calendar/events/1')
        
        assert response.status_code == 401


class TestCalendarBirthdays:
    """Testes para GET /api/calendar/birthdays"""
    
    def test_get_birthdays_success(self, client, admin_headers):
        """Obter lista de aniversários"""
        response = client.get(
            '/api/calendar/birthdays',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'birthdays' in data or isinstance(data, list)
    
    def test_get_birthdays_unauthenticated(self, client):
        """Obter aniversários sem autenticação"""
        response = client.get('/api/calendar/birthdays')
        
        assert response.status_code == 401


class TestCalendarMarkPosted:
    """Testes para marcar evento como postado"""
    
    def test_mark_event_posted(self, client, app, admin_user, admin_headers):
        """Marcar evento como postado"""
        with app.app_context():
            from app.models.calendar_event import CalendarEvent
            from app.extensions.database import db
            
            event = CalendarEvent(
                title='Test Event',
                description='Test',
                start_date=datetime.utcnow() + timedelta(days=1),
                end_date=datetime.utcnow() + timedelta(days=1, hours=2),
                event_type='meeting',
                created_by=admin_user.id
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id
        
        response = client.put(
            f'/api/calendar/events/{event_id}/mark-posted',
            headers=admin_headers
        )
        
        assert response.status_code == 200
    
    def test_mark_event_posted_not_found(self, client, admin_headers):
        """Marcar evento inexistente como postado"""
        response = client.put(
            '/api/calendar/events/99999/mark-posted',
            headers=admin_headers
        )
        
        assert response.status_code == 404
