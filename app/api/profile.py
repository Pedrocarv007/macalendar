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
from app.models.settings import UserSettings
from app.extensions.database import csrf

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
        return jsonify({'error': 'Erro ao obter perfil'}), 500

@profile_bp.route('/me', methods=['PUT'])
@api_login_required
def update_profile():
    """Atualizar dados do perfil do usuário"""
    try:
        user_id = g.get('current_user_id')
        data = request.get_json()
        
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
                except ValueError:
                    return jsonify({'error': 'Formato de data de nascimento inválido'}), 400
            
            if 'hireDate' in data and data['hireDate']:
                try:
                    employee.hire_date = datetime.strptime(data['hireDate'], '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': 'Formato de data de contratação inválido'}), 400
        
        # Atualizar timestamp
        employee.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Perfil atualizado com sucesso',
            'user': employee.to_dict()
        }), 200
        
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro ao atualizar perfil'}), 500

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
        return jsonify({'error': 'Erro ao processar foto'}), 500

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
        return jsonify({'error': 'Erro ao deletar foto'}), 500

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
        return jsonify({'error': 'Erro ao alterar senha'}), 500

@profile_bp.route('/settings', methods=['GET'])
@api_login_required
def get_user_settings():
    """Obter configurações do usuário atual."""
    try:
        user_id = g.get('current_user_id')
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        if not settings:
            # Não criar ainda; apenas retornar defaults
            defaults = UserSettings(user_id=user_id)  # usa defaults do modelo
            return jsonify({'settings': defaults.to_dict()}), 200
        return jsonify({'settings': settings.to_dict()}), 200
    except Exception:
        return jsonify({'error': 'Erro ao obter configurações'}), 500

@profile_bp.route('/settings', methods=['PUT'])
@api_login_required
@csrf.exempt
def update_user_settings():
    """Criar/atualizar configurações do usuário atual."""
    try:
        user_id = g.get('current_user_id')
        data = request.get_json() or {}

        settings = UserSettings.query.filter_by(user_id=user_id).first()
        created = False
        if not settings:
            settings = UserSettings(user_id=user_id)
            created = True

        # Mapear campos recebidos
        if 'timezone' in data:
            settings.timezone = str(data['timezone']) or settings.timezone
        if 'notifications_enabled' in data:
            raw = data['notifications_enabled']
            settings.notifications_enabled = (str(raw).lower() in ['true','1','yes','on']) if isinstance(raw, str) else bool(raw)
        if 'email_notifications' in data:
            raw = data['email_notifications']
            settings.email_notifications = (str(raw).lower() in ['true','1','yes','on']) if isinstance(raw, str) else bool(raw)
        if 'two_factor_enabled' in data:
            raw = data['two_factor_enabled']
            settings.two_factor_enabled = (str(raw).lower() in ['true','1','yes','on']) if isinstance(raw, str) else bool(raw)
        if 'auto_logout_enabled' in data:
            raw = data['auto_logout_enabled']
            settings.auto_logout_enabled = (str(raw).lower() in ['true','1','yes','on']) if isinstance(raw, str) else bool(raw)
        if 'session_timeout_minutes' in data:
            try:
                settings.session_timeout_minutes = int(data['session_timeout_minutes'])
            except Exception:
                pass
        if 'items_per_page' in data:
            try:
                settings.items_per_page = int(data['items_per_page'])
            except Exception:
                pass
        if 'dark_mode' in data:
            raw = data['dark_mode']
            settings.dark_mode = (str(raw).lower() in ['true','1','yes','on']) if isinstance(raw, str) else bool(raw)

        settings.updated_at = datetime.utcnow()
        if created:
            db.session.add(settings)
        db.session.commit()

        return jsonify({'message': 'Configurações salvas', 'settings': settings.to_dict()}), 200
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro ao salvar configurações'}), 500
