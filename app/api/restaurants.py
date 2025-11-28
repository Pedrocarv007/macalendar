"""
Rotas da API de Restaurantes
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import get_jwt_identity, get_jwt
from datetime import datetime
from app.extensions.database import db
from app.models.restaurant import Restaurant
from app.models.employee import Employee
from app.middleware.security import api_login_required, role_required

restaurants_bp = Blueprint('restaurants', __name__)

@restaurants_bp.route('', methods=['GET'])
@api_login_required
def get_restaurants():
    """Obter lista de restaurantes"""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        # Parâmetros de filtro
        is_active = request.args.get('is_active', 'true').lower() == 'true'
        
        # Query base
        query = Restaurant.query
        
        # Filtrar por status
        query = query.filter(Restaurant.is_active == is_active)
        
        # Filtrar por permissões
        if user_role not in ['admin', 'rh', 'marketing']:
            # Usuários não admin só veem seu próprio restaurante
            if user_restaurant_id:
                query = query.filter(Restaurant.id == user_restaurant_id)
            else:
                return jsonify({'restaurants': []}), 200
        
        restaurants = query.all()
        
        return jsonify({
            'restaurants': [restaurant.to_dict() for restaurant in restaurants]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@restaurants_bp.route('', methods=['POST'])
@api_login_required
@role_required('admin', 'rh')
def create_restaurant():
    """Criar novo restaurante"""
    try:
        current_user_id = g.get('current_user_id')
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Validar dados obrigatórios
        if not data.get('name'):
            return jsonify({'error': 'Nome do restaurante é obrigatório'}), 400
        
        # Verificar se já existe restaurante com este nome
        existing = Restaurant.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({'error': 'Já existe um restaurante com este nome'}), 409
        
        # Verificar se manager_id é válido
        manager_id = data.get('manager_id')
        if manager_id:
            manager = Employee.query.get(manager_id)
            if not manager:
                return jsonify({'error': 'Gerente não encontrado'}), 404
            if manager.role not in ['manager', 'admin']:
                return jsonify({'error': 'Usuário não pode ser gerente'}), 400
        
        # Criar restaurante
        restaurant = Restaurant(
            name=data['name'],
            address=data.get('address'),
            phone=data.get('phone'),
            email=data.get('email'),
            manager_id=manager_id
        )
        
        db.session.add(restaurant)
        db.session.commit()
        
        return jsonify({
            'message': 'Restaurante criado com sucesso',
            'restaurant': restaurant.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@restaurants_bp.route('/<int:restaurant_id>', methods=['PUT'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def update_restaurant(restaurant_id):
    """Atualizar restaurante"""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            return jsonify({'error': 'Restaurante não encontrado'}), 404
        
        # Verificar permissões
        if user_role == 'manager' and restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Atualizar campos
        if 'name' in data:
            # Verificar se nome já existe (exceto o próprio restaurante)
            existing = Restaurant.query.filter_by(name=data['name']).first()
            if existing and existing.id != restaurant_id:
                return jsonify({'error': 'Já existe um restaurante com este nome'}), 409
            restaurant.name = data['name']
        
        if 'address' in data:
            restaurant.address = data['address']
        if 'phone' in data:
            restaurant.phone = data['phone']
        if 'email' in data:
            restaurant.email = data['email']
        
        # Apenas admin e RH podem alterar gerente
        if 'manager_id' in data and user_role in ['admin', 'rh']:
            manager_id = data['manager_id']
            if manager_id:
                manager = Employee.query.get(manager_id)
                if not manager:
                    return jsonify({'error': 'Gerente não encontrado'}), 404
                if manager.role not in ['manager', 'admin']:
                    return jsonify({'error': 'Usuário não pode ser gerente'}), 400
            restaurant.manager_id = manager_id
        
        # Apenas admin pode alterar status
        if 'is_active' in data and user_role == 'admin':
            restaurant.is_active = data['is_active']
        
        restaurant.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Restaurante atualizado com sucesso',
            'restaurant': restaurant.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@restaurants_bp.route('/<int:restaurant_id>', methods=['DELETE'])
@api_login_required
@role_required('admin')
def delete_restaurant(restaurant_id):
    """Deletar restaurante (soft delete) - apenas admin"""
    try:
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            return jsonify({'error': 'Restaurante não encontrado'}), 404
        
        # Soft delete
        restaurant.is_active = False
        restaurant.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Restaurante removido com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@restaurants_bp.route('/<int:restaurant_id>/stats', methods=['GET'])
@api_login_required
def get_restaurant_stats(restaurant_id):
    """Obter estatísticas do restaurante"""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        # Verificar permissões
        if user_role not in ['admin', 'rh', 'marketing']:
            if restaurant_id != user_restaurant_id:
                return jsonify({'error': 'Permissão negada'}), 403
        
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            return jsonify({'error': 'Restaurante não encontrado'}), 404
        
        # Calcular estatísticas
        from app.models.employee import Employee
        from app.models.calendar_event import CalendarEvent
        
        total_employees = Employee.query.filter_by(
            restaurant_id=restaurant_id, 
            is_active=True
        ).count()
        
        # Aniversariantes do mês
        current_month = datetime.now().month
        birthdays_this_month = Employee.query.filter(
            Employee.restaurant_id == restaurant_id,
            Employee.is_active == True,
            db.extract('month', Employee.birth_date) == current_month
        ).count()
        
        # Eventos este mês
        current_year = datetime.now().year
        events_this_month = CalendarEvent.query.filter(
            CalendarEvent.restaurant_id == restaurant_id,
            db.extract('year', CalendarEvent.start_date) == current_year,
            db.extract('month', CalendarEvent.start_date) == current_month
        ).count()
        
        return jsonify({
            'restaurant': restaurant.to_dict(),
            'stats': {
                'total_employees': total_employees,
                'birthdays_this_month': birthdays_this_month,
                'events_this_month': events_this_month
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500