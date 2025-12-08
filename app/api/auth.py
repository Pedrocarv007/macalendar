"""
Rotas de autenticação da API
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, get_jwt
from datetime import datetime
from app.extensions.database import db
from app.models.employee import Employee
from app.models.restaurant import Restaurant
from app.middleware.security import validate_email, validate_password_strength, role_required

auth_bp = Blueprint('auth', __name__)

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
        
        return jsonify({
            'access_token': access_token,
            'user': employee.to_dict(),
            'message': 'Login realizado com sucesso'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/register', methods=['POST'])
@jwt_required()
@role_required('admin', 'rh')
def register():
    """Registro de novo usuário (apenas para admins e RH)"""
    try:
        current_user_id = int(get_jwt_identity())
        current_user = Employee.query.get(current_user_id)
        
        if not current_user:
            return jsonify({'error': 'Usuário atual não encontrado'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Validar dados obrigatórios
        required_fields = ['email', 'password', 'name', 'role']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} é obrigatório'}), 400
        
        email = data['email'].strip().lower()
        password = data['password']
        name = data['name'].strip()
        role = data['role'].lower()
        
        # Validações
        if not validate_email(email):
            return jsonify({'error': 'Formato de email inválido'}), 400
        
        is_valid, message = validate_password_strength(password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        valid_roles = ['admin', 'rh', 'marketing', 'manager', 'employee']
        if role not in valid_roles:
            return jsonify({'error': f'Role inválido. Deve ser um de: {", ".join(valid_roles)}'}), 400
        
        # Verificar se email já existe
        if Employee.query.filter_by(email=email).first():
            return jsonify({'error': 'Email já cadastrado'}), 409
        
        # Verificar restaurante se fornecido
        restaurant_id = data.get('restaurant_id')
        if restaurant_id:
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant:
                return jsonify({'error': 'Restaurante não encontrado'}), 404
            
            if not restaurant.is_active:
                return jsonify({'error': 'Restaurante inativo'}), 400
        
        # Criar novo employee (agora funciona como user também)
        new_employee = Employee(
            email=email,
            name=name,
            role=role,
            department=data.get('department'),
            restaurant_id=restaurant_id or 1,  # Default restaurant
            position=name,  # Usar nome como posição
            birth_date=datetime.utcnow().date()  # Data padrão
        )
        new_employee.set_password(password)
        
        db.session.add(new_employee)
        db.session.commit()
        
        return jsonify({
            'message': 'Usuário criado com sucesso',
            'user': new_employee.to_dict()
        }), 201
        
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
            from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
        except:
            # Se JWT falhar, usar sessão
            from flask import session
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
    from flask import session
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Não autenticado'}), 401
        
        employee = Employee.query.get(session.get('user_id'))
        
        if not employee:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        return jsonify(employee.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
def get_current_user_web():
    """Obter dados do usuário logado via sessão (para aplicação web)"""
    try:
        from flask import session
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Não autenticado'}), 401
        
        employee = Employee.query.get(user_id)
        if not employee:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        return jsonify(employee.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
        
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