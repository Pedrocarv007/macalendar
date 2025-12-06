"""
Rotas da API de Restaurantes
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import get_jwt_identity, get_jwt
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from PIL import Image
from app.extensions.database import db
from app.models.restaurant import Restaurant
from app.models.employee import Employee
from app.middleware.security import api_login_required, role_required, allowed_file

restaurants_bp = Blueprint('restaurants', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

@restaurants_bp.route('', methods=['GET'])
@api_login_required
def get_restaurants():
    """Obter lista de restaurantes"""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        # Query base - carregar TODOS os restaurantes (ativos e inativos)
        query = Restaurant.query
        
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
            capacity=data.get('capacity'),
            opening_hours=data.get('opening_hours'),
            description=data.get('description'),
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
        if 'capacity' in data:
            restaurant.capacity = data.get('capacity')
        if 'opening_hours' in data:
            restaurant.opening_hours = data['opening_hours']
        if 'description' in data:
            restaurant.description = data['description']
        
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
        
        # Admin e RH podem alterar status
        if 'is_active' in data and user_role in ['admin', 'rh']:
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

@restaurants_bp.route('/<int:restaurant_id>/upload-photo', methods=['POST'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def upload_restaurant_photo(restaurant_id):
    """Upload de foto para restaurante"""
    try:
        # Verificar se arquivo foi enviado
        if 'file' not in request.files:
            return jsonify({'error': 'Arquivo não fornecido'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Arquivo não selecionado'}), 400
        
        # Verificar extensão
        if not allowed_file(file.filename, ALLOWED_EXTENSIONS):
            return jsonify({'error': 'Formato de arquivo não permitido. Use PNG, JPG, JPEG ou GIF'}), 400
        
        # Verificar se restaurante existe
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            return jsonify({'error': 'Restaurante não encontrado'}), 404
        
        # Verificar permissões
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        if user_role not in ['admin', 'rh'] and restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada'}), 403
        
        try:
            # Criar pasta se não existir
            upload_folder = 'app/static/uploads/restaurants'
            os.makedirs(upload_folder, exist_ok=True)
            
            # Gerar nome seguro do arquivo
            filename = secure_filename(f"restaurant_{restaurant_id}_{datetime.now().timestamp()}.jpg")
            filepath = os.path.join(upload_folder, filename)
            
            # Redimensionar e otimizar imagem
            img = Image.open(file)
            
            # Converter para RGB se necessário
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Redimensionar para 600x400 máximo
            img.thumbnail((600, 400), Image.Resampling.LANCZOS)
            
            # Salvar com qualidade otimizada
            img.save(filepath, 'JPEG', quality=85, optimize=True)
            
            # Deletar foto antiga se existir
            if restaurant.photo_filename:
                old_path = os.path.join('app/static/uploads/restaurants', restaurant.photo_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            # Atualizar banco de dados
            restaurant.photo_filename = filename
            restaurant.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'message': 'Foto enviada com sucesso',
                'photo_filename': filename,
                'photo_url': f'/static/uploads/restaurants/{filename}'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Erro ao processar imagem: {str(e)}'}), 500
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@restaurants_bp.route('/<int:restaurant_id>/photo', methods=['DELETE'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def delete_restaurant_photo(restaurant_id):
    """Deletar foto do restaurante"""
    try:
        # Verificar se restaurante existe
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            return jsonify({'error': 'Restaurante não encontrado'}), 404
        
        # Verificar permissões
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        if user_role not in ['admin', 'rh'] and restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada'}), 403
        
        if restaurant.photo_filename:
            # Deletar arquivo
            old_path = os.path.join('app/static/uploads/restaurants', restaurant.photo_filename)
            if os.path.exists(old_path):
                os.remove(old_path)
            
            # Atualizar banco
            restaurant.photo_filename = None
            restaurant.updated_at = datetime.utcnow()
            db.session.commit()
        
        return jsonify({'message': 'Foto deletada com sucesso'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500