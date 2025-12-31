"""
Rotas de autenticação da API
"""
from datetime import datetime
import requests
from flask import Blueprint, redirect, request, jsonify, session, url_for
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    verify_jwt_in_request,
)

from app.extensions.database import db
from app.middleware.security import validate_email, validate_password_strength, role_required
from app.utils.notifications import notify_login
from app.models.employee import Employee
from app.models.restaurant import Restaurant

auth_bp = Blueprint('auth', __name__)


def _ensure_default_restaurant():
    """Garantir que exista um restaurante padrão para associação automática."""
    default = Restaurant.query.filter_by(name='Restaurante Padrão').first()
    if default:
        return default

    default = Restaurant(
        name='Restaurante Padrão',
        address='Atualize este endereço',
        phone='910000000',
        email='default@mac.com',
        is_active=True
    )
    db.session.add(default)
    db.session.commit()
    return default

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login do usuário"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email e senha são obrigatórios'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Formato de email inválido'}), 400
        
        # Buscar employee (agora funciona como user também)
        employee = Employee.query.filter_by(email=email).first()
        
        if not employee or not employee.check_password(password):
            return jsonify({'error': 'Credenciais inválidas'}), 401
        
        if not employee.is_active:
            return jsonify({'error': 'Conta inativa. Entre em contato com o administrador'}), 401
        
        # Atualizar último login
        employee.last_login = datetime.utcnow()
        db.session.commit()
        
        # Criar token de acesso
        additional_claims = {
            'role': employee.role,
            'restaurant_id': employee.restaurant_id,
            'department': employee.department,
            'name': employee.name
        }
        
        access_token = create_access_token(
            identity=str(employee.id),
            additional_claims=additional_claims
        )

        # Notificação de login (opcional, respeita user settings)
        try:
            notify_login(employee)
        except Exception:
            pass
        
        return jsonify({
            'access_token': access_token,
            'user': employee.to_dict(),
            'message': 'Login realizado com sucesso'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Obter perfil do usuário atual"""
    try:
        current_user_id = int(get_jwt_identity())
        employee = Employee.query.get(current_user_id)
        
        if not employee:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        return jsonify({
            'user': employee.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Obter dados do usuário logado (agora employee direto)"""
    try:
        current_user_id = int(get_jwt_identity())
        employee = Employee.query.get(current_user_id)
        
        if not employee:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        return jsonify(employee.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/current-user', methods=['GET'])
def get_current_user_session():
    """Obter dados do usuário logado via sessão ou JWT"""
    try:
        # Tentar primeiro com JWT
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
        except Exception:
            # Se JWT falhar, usar sessão
            if 'user_id' not in session:
                return jsonify({'error': 'Não autenticado'}), 401
            current_user_id = session.get('user_id')
        
        if not current_user_id:
            return jsonify({'error': 'Não autenticado'}), 401
        
        employee = Employee.query.get(current_user_id)
        
        if not employee:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        return jsonify(employee.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/user', methods=['GET'])
def get_user_session():
    """Alias para /current-user (compatibilidade)"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Não autenticado'}), 401
        
        user_id = session.get('user_id')
        employee = Employee.query.get(user_id)
        
        if not employee:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        return jsonify(employee.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Atualizar perfil do usuário"""
    try:
        current_user_id = int(get_jwt_identity())
        employee = Employee.query.get(current_user_id)
        
        if not employee:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Campos que podem ser atualizados pelo próprio usuário
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({'error': 'Nome não pode estar vazio'}), 400
            employee.name = name
        
        if 'email' in data:
            email = data['email'].strip().lower()
            if not validate_email(email):
                return jsonify({'error': 'Formato de email inválido'}), 400
            
            # Verificar se email já existe (exceto o próprio usuário)
            existing_employee = Employee.query.filter_by(email=email).first()
            if existing_employee and existing_employee.id != employee.id:
                return jsonify({'error': 'Email já cadastrado'}), 409
            
            employee.email = email
        
        employee.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Perfil atualizado com sucesso',
            'user': employee.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Alterar senha do usuário"""
    try:
        current_user_id = int(get_jwt_identity())
        employee = Employee.query.get(current_user_id)
        
        if not employee:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Senha atual e nova senha são obrigatórias'}), 400
        
        if not employee.check_password(current_password):
            return jsonify({'error': 'Senha atual incorreta'}), 400
        
        is_valid, message = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        employee.set_password(new_password)
        employee.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Senha alterada com sucesso'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/users', methods=['GET'])
@jwt_required()
@role_required('admin', 'rh')
def list_users():
    """Listar usuários/employees (apenas admin e RH)"""
    try:
        claims = get_jwt()
        user_role = claims.get('role')
        user_restaurant_id = claims.get('restaurant_id')
        
        # Parâmetros de filtro
        restaurant_id = request.args.get('restaurant_id', type=int)
        role = request.args.get('role')
        is_active = request.args.get('is_active', 'true').lower() == 'true'
        
        # Query base - agora usando Employee
        query = Employee.query
        
        # Filtros
        if is_active is not None:
            query = query.filter(Employee.is_active == is_active)
        
        if role:
            query = query.filter(Employee.role == role)
        
        if restaurant_id:
            query = query.filter(Employee.restaurant_id == restaurant_id)
        elif user_role == 'rh' and user_restaurant_id:
            # RH só vê employees do próprio restaurante
            query = query.filter(Employee.restaurant_id == user_restaurant_id)
        
        employees = query.all()
        
        return jsonify({
            'users': [employee.to_dict() for employee in employees]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
    



