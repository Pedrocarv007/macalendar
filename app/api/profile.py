"""
Rotas da API de Perfil do Usuário
"""
import os
from datetime import datetime

from flask import Blueprint, request, jsonify, g, session
from PIL import Image
from werkzeug.utils import secure_filename

from app.extensions.database import db
from app.middleware.security import (
    allowed_file,
    api_login_required,
    validate_password_strength,
)
from app.models.employee import Employee

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/me', methods=['GET'])
@api_login_required
def get_profile():
    """Obter dados do perfil do usuário autenticado"""
    try:
        user_id = g.get('current_user_id')
        
        employee = Employee.query.get(user_id)
        if not employee:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        return jsonify(employee.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@profile_bp.route('/me', methods=['PUT'])
@api_login_required
def update_profile():
    """Atualizar dados do perfil do usuário"""
    try:
        user_id = g.get('current_user_id')
        data = request.get_json()
        
        print(f"[PROFILE UPDATE] User ID: {user_id}, Data recebida: {data}")
        
        employee = Employee.query.get(user_id)
        if not employee:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Atualizar campos permitidos
        if 'name' in data:
            employee.name = data['name']
        
        if 'phone' in data:
            employee.phone = data['phone']
        
        if 'address' in data:
            employee.address = data['address']
        
        if 'notes' in data:
            employee.notes = data['notes']
        
        if 'position' in data:
            employee.position = data['position']
        
        if 'department' in data:
            employee.department = data['department']
        
        if 'role' in data:
            # Somente admins podem alterar a função no sistema
            user_role = g.get('current_user_role')
            if user_role == 'admin':
                employee.role = data['role']
        
        # Somente admins podem editar datas
        user_role = g.get('current_user_role')
        if user_role == 'admin':
            if 'birthDate' in data and data['birthDate']:
                try:
                    employee.birth_date = datetime.strptime(data['birthDate'], '%Y-%m-%d').date()
                    print(f"[PROFILE UPDATE] Birth date atualizada para: {employee.birth_date}")
                except ValueError as e:
                    print(f"[PROFILE UPDATE] Erro ao parsear birthDate: {e}")
                    return jsonify({'error': 'Formato de data de nascimento inválido'}), 400
            
            if 'hireDate' in data and data['hireDate']:
                try:
                    employee.hire_date = datetime.strptime(data['hireDate'], '%Y-%m-%d').date()
                    print(f"[PROFILE UPDATE] Hire date atualizada para: {employee.hire_date}")
                except ValueError as e:
                    print(f"[PROFILE UPDATE] Erro ao parsear hireDate: {e}")
                    return jsonify({'error': 'Formato de data de contratação inválido'}), 400
        
        # Atualizar timestamp
        employee.updated_at = datetime.utcnow()
        
        db.session.commit()
        print(f"[PROFILE UPDATE] Salvo com sucesso para user {user_id}")
        
        return jsonify({
            'message': 'Perfil atualizado com sucesso',
            'user': employee.to_dict()
        }), 200
        
    except Exception as e:
        print(f"[PROFILE UPDATE] Erro: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Erro ao atualizar perfil: {str(e)}'}), 500

@profile_bp.route('/me/photo', methods=['POST'])
@api_login_required
def upload_profile_photo():
    """Upload de foto do perfil"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Arquivo não fornecido'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Arquivo não selecionado'}), 400
        
        # Verificar extensão
        if not allowed_file(file.filename, {'png', 'jpg', 'jpeg', 'gif'}):
            return jsonify({'error': 'Formato de arquivo não permitido'}), 400
        
        user_id = g.get('current_user_id')
        employee = Employee.query.get(user_id)
        if not employee:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Criar pasta de uploads se não existir
        upload_folder = 'app/static/uploads/employees'
        os.makedirs(upload_folder, exist_ok=True)
        
        # Gerar nome seguro do arquivo
        filename = secure_filename(f"employee_{employee.id}_{datetime.now().timestamp()}.jpg")
        filepath = os.path.join(upload_folder, filename)
        
        # Redimensionar e otimizar imagem
        img = Image.open(file)
        
        # Converter para RGB se necessário
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Redimensionar para 400x400
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
        
        # Salvar com qualidade otimizada
        img.save(filepath, 'JPEG', quality=85, optimize=True)
        
        # Deletar foto antiga se existir
        if employee.photo_filename:
            old_path = os.path.join('app/static/uploads/employees', employee.photo_filename)
            if os.path.exists(old_path):
                os.remove(old_path)
        
        # Atualizar banco
        employee.photo_filename = filename
        employee.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Foto enviada com sucesso',
            'photo_filename': filename,
            'photo_url': f'/static/uploads/employees/{filename}'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro ao processar foto: {str(e)}'}), 500

@profile_bp.route('/me/photo', methods=['DELETE'])
@api_login_required
def delete_profile_photo():
    """Deletar foto do perfil"""
    try:
        user_id = g.get('current_user_id')
        employee = Employee.query.get(user_id)
        if not employee:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        if employee.photo_filename:
            old_path = os.path.join('app/static/uploads/employees', employee.photo_filename)
            if os.path.exists(old_path):
                os.remove(old_path)
            
            employee.photo_filename = None
            employee.updated_at = datetime.utcnow()
            db.session.commit()
        
        return jsonify({'message': 'Foto deletada com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro ao deletar foto: {str(e)}'}), 500

@profile_bp.route('/me/password', methods=['POST'])
@api_login_required
def change_password():
    """Alterar senha do usuário"""
    try:
        user_id = g.get('current_user_id')
        data = request.get_json()
        
        # Validar dados
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'Senha atual e nova senha são obrigatórias'}), 400
        
        employee = Employee.query.get(user_id)
        if not employee:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Verificar senha atual
        if not employee.check_password(data['current_password']):
            return jsonify({'error': 'Senha atual incorreta'}), 401
        
        is_valid, message = validate_password_strength(data['new_password'])
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Definir nova senha
        employee.set_password(data['new_password'])
        employee.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Limpar flag de mudança obrigatória de senha no primeiro login
        session.pop('must_change_pw', None)
        
        return jsonify({'message': 'Senha alterada com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro ao alterar senha: {str(e)}'}), 500
