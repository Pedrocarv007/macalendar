from flask import session, request, jsonify
from sqlalchemy import or_
from datetime import datetime
from app.models.calendar_event import CalendarEvent

def get_events():
    """Obter eventos do calendário com filtros de permissão e data"""
    try:
        # 1. Obter contexto do usuário
        user_role = session["user_role"]
        user_restaurant_id = session["restaurant_id"]
        
        # 2. Parâmetros da Query
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        include_global = request.args.get('include_global', '').lower() == 'true'
        
        query = CalendarEvent.query
        
        # 3. Lógica de Permissões Consolidada
        # Admins/RH/Marketing veem tudo, outros são filtrados por restaurante
        if user_role not in ['admin', 'rh', 'marketing']:
            conditions = [CalendarEvent.restaurant_id == user_restaurant_id]
            
            if include_global:
                conditions.append(CalendarEvent.restaurant_id.is_(None))
            
            query = query.filter(or_(*conditions))
        
        # 4. Filtro de Período (Overlapping Check)
        # Um evento intersecta o período se (Início <= FimBusca) E (Fim >= InícioBusca)
        if start_date:
            query = query.filter(CalendarEvent.end_date >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(CalendarEvent.start_date <= datetime.fromisoformat(end_date))
        
        # 5. Execução e Resposta
        events = query.order_by(CalendarEvent.start_date.asc()).all()
        
        return jsonify({
            'count': len(events),
            'events': [event.to_dict() for event in events]
        }), 200
        
    except ValueError:
        return jsonify({'error': 'Formato de data inválido. Use ISO8601.'}), 400
    except Exception as e:
        # Em produção, use logging em vez de retornar o erro cru
        return jsonify({'error': 'Erro interno ao processar eventos.'}), 500