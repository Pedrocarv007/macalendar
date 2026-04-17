"""
Rotas da API do Calendário
Refatorado para usar CalendarService e MysteryService
"""
from flask import Blueprint, request, jsonify, g
from datetime import datetime
from app.middleware.security import api_login_required
from app.services.calendar.calendar_service import CalendarService
from app.services.calendar.mystery_service import MysteryService

calendar_bp = Blueprint('calendar', __name__)

def get_service(service_class=CalendarService):
    """Instancia o serviço com o contexto do usuário atual."""
    return service_class(
        user_id=g.get('current_user_id'),
        user_role=g.get('current_user_role'),
        user_restaurant_id=g.get('current_user_restaurant_id')
    )

@calendar_bp.route('/events', methods=['GET'])
@api_login_required
def get_events():
    """Obter eventos do calendário"""
    try:
        service = get_service()
        events = service.list_events(
            start_date=request.args.get('start'),
            end_date=request.args.get('end'),
            include_global=(request.args.get('include_global') or '').lower() == 'true'
        )
        return jsonify({'events': [e.to_dict() for e in events]}), 200
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@calendar_bp.route('/events', methods=['POST'])
@api_login_required
def create_event():
    """Criar novo evento"""
    try:
        service = get_service()
        
        # Suporte a multipart/form-data ou JSON
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            data = request.form.to_dict()
            file = request.files.get('photo')
        else:
            data = request.get_json()
            file = None

        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        event = service.create_event(data, file)
        
        return jsonify({
            'message': 'Evento criado com sucesso',
            'event': event.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@calendar_bp.route('/events/<int:event_id>', methods=['PUT'])
@api_login_required
def update_event(event_id):
    """Atualizar evento"""
    try:
        service = get_service()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
            
        event = service.update_event(event_id, data)
        if not event:
            return jsonify({'error': 'Evento não encontrado'}), 404
            
        return jsonify({
            'message': 'Evento atualizado com sucesso',
            'event': event.to_dict()
        }), 200
        
    except PermissionError:
        return jsonify({'error': 'Permissão negada'}), 403
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@calendar_bp.route('/events/<int:event_id>', methods=['DELETE'])
@api_login_required
def delete_event(event_id):
    """Deletar evento"""
    try:
        service = get_service()
        success = service.delete_event(event_id)
        
        if not success:
            return jsonify({'error': 'Evento não encontrado'}), 404
            
        return jsonify({'message': 'Evento deletado com sucesso'}), 200
        
    except PermissionError:
        return jsonify({'error': 'Permissão negada'}), 403
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@calendar_bp.route('/events/<int:event_id>/mark-posted', methods=['PUT'])
@api_login_required
def mark_event_posted(event_id):
    """Marcar evento como postado"""
    try:
        service = get_service()
        event = service.mark_posted(event_id)
        
        if not event:
            return jsonify({'error': 'Evento não encontrado'}), 404
            
        return jsonify({
            'message': 'Evento marcado como postado', 
            'event': event.to_dict()
        }), 200
        
    except PermissionError:
        return jsonify({'error': 'Permissão negada'}), 403
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@calendar_bp.route('/birthdays', methods=['GET'])
@api_login_required
def get_birthdays():
    """Obter aniversários do mês"""
    try:
        service = get_service()
        month = request.args.get('month', type=int) or datetime.utcnow().month
        year = request.args.get('year', type=int) or datetime.utcnow().year
        
        birthdays = service.get_birthdays(month, year)
        return jsonify({'birthdays': birthdays}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

# --- Rotas de Geração IA (Mystery Service) ---

@calendar_bp.route('/generate/mystery-tuesdays', methods=['POST'])
@api_login_required
def generate_mystery_tuesdays():
    """Gerar eventos de 'Desafio Mistério' (Terças)"""
    try:
        service = get_service(MysteryService)
        data = request.get_json() or {}
        
        events = service.generate_tuesdays(data)
        
        return jsonify({
            'message': 'Desafios gerados com sucesso',
            'count': len(events),
            'events': [e.to_dict() for e in events]
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except PermissionError:
        return jsonify({'error': 'Permissão negada'}), 403
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@calendar_bp.route('/generate/mystery-answers', methods=['POST'])
@api_login_required
def generate_mystery_answers():
    """Gerar respostas dos desafios (Sábados)"""
    try:
        service = get_service(MysteryService)
        data = request.get_json() or {}
        
        events = service.generate_answers_bulk(data)
        
        return jsonify({
            'message': 'Respostas geradas com sucesso',
            'count': len(events),
            'events': [e.to_dict() for e in events]
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except PermissionError:
        return jsonify({'error': 'Permissão negada'}), 403
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
