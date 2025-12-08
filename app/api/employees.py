"""
Rotas da API de Colaboradores
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os
from PIL import Image
from app.extensions.database import db
from app.models.employee import Employee
from app.models.restaurant import Restaurant
from app.middleware.security import api_login_required, role_required, allowed_file

employees_bp = Blueprint('employees', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

@employees_bp.route('', methods=['GET'])
@api_login_required
def get_employees():
    """Obter lista de colaboradores"""
    try:
        # Usar dados de g (setados pelo decorator)
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        # Parâmetros de filtro
        restaurant_id = request.args.get('restaurant_id', type=int)
        
        # Query base
        query = Employee.query
        
        # Filtrar por permissões
        if user_role in ['admin', 'rh', 'marketing']:
            # Pode ver todos os restaurantes
            if restaurant_id:
                query = query.filter(Employee.restaurant_id == restaurant_id)
        else:
            # Só pode ver do próprio restaurante
            if user_restaurant_id:
                query = query.filter(Employee.restaurant_id == user_restaurant_id)
            else:
                return jsonify({'employees': []}), 200
        
        employees = query.all()
        
        return jsonify({
            'employees': [employee.to_dict() for employee in employees]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@employees_bp.route('', methods=['POST'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def create_employee():
    """Criar novo colaborador"""
    try:
        current_user_id = g.get('current_user_id')
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        data = request.get_json()
        
                # DEBUG: Ver o que está sendo enviado
        print("DEBUG - Dados recebidos:", data)
        print("DEBUG - User role:", user_role)
        print("DEBUG - User restaurant_id:", user_restaurant_id)

        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Validar dados obrigatórios
        required_fields = ['name', 'position', 'birth_date', 'restaurant_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} é obrigatório'}), 400
        
        # Verificar se o usuário pode criar funcionário neste restaurante
        restaurant_id = data['restaurant_id']
        if user_role not in ['admin', 'rh'] and restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada para este restaurante'}), 403
        
        # Verificar se restaurante existe
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            return jsonify({'error': 'Restaurante não encontrado'}), 404
        
        try:
            birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400
        
        # Converter hire_date apenas se fornecido (agora é opcional)
        hire_date = None
        if data.get('hire_date'):
            try:
                hire_date = datetime.strptime(data['hire_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de data de contratação inválido. Use YYYY-MM-DD'}), 400
        # Criar colaborador
        employee = Employee(
            name=data['name'],
            email=data.get('email'),
            phone=data.get('phone'),
            position=data['position'],
            department=data.get('department'),
            address=data.get('address'),
            birth_date=birth_date,
            hire_date=hire_date,
            restaurant_id=restaurant_id,
            notes=data.get('notes')
        )
        
        db.session.add(employee)
        db.session.commit()
        
        return jsonify({
            'message': 'Colaborador criado com sucesso',
            'employee': employee.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG - Erro ao criar colaborador: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@employees_bp.route('/<int:employee_id>', methods=['GET'])
@api_login_required
def get_employee(employee_id):
    """Obter colaborador por ID"""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return jsonify({'error': 'Colaborador não encontrado'}), 404
        
        # Verificar permissões
        if user_role not in ['admin', 'rh', 'marketing'] and employee.restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada'}), 403
        
        return jsonify({'employee': employee.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@employees_bp.route('/<int:employee_id>', methods=['PUT'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def update_employee(employee_id):
    """Atualizar colaborador"""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({'error': 'Colaborador não encontrado'}), 404
        
        # Verificar permissões
        if user_role not in ['admin', 'rh']:
            if employee.restaurant_id != user_restaurant_id:
                return jsonify({'error': 'Permissão negada'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Atualizar campos
        if 'name' in data:
            employee.name = data['name']
        if 'email' in data:
            employee.email = data['email']
        if 'phone' in data:
            employee.phone = data['phone']
        if 'position' in data:
            employee.position = data['position']
        if 'department' in data:
            employee.department = data['department']
        if 'address' in data:
            employee.address = data['address']
        if 'birth_date' in data:
            employee.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
        if 'hire_date' in data:
            employee.hire_date = datetime.strptime(data['hire_date'], '%Y-%m-%d').date()
        if 'is_active' in data:
            employee.is_active = data['is_active']
        if 'notes' in data:
            employee.notes = data['notes']
        if 'restaurant_id' in data:
            # Validar restaurante
            restaurant = Restaurant.query.get(data['restaurant_id'])
            if not restaurant:
                return jsonify({'error': 'Restaurante não encontrado'}), 404
            employee.restaurant_id = data['restaurant_id']
        
        employee.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Colaborador atualizado com sucesso',
            'employee': employee.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@employees_bp.route('/<int:employee_id>/photo', methods=['POST'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def upload_photo(employee_id):
    """Upload de foto do colaborador"""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({'error': 'Colaborador não encontrado'}), 404
        
        # Verificar permissões
        if user_role not in ['admin', 'rh']:
            if employee.restaurant_id != user_restaurant_id:
                return jsonify({'error': 'Permissão negada'}), 403
        
        if 'photo' not in request.files:
            return jsonify({'error': 'Nenhuma foto enviada'}), 400
        
        file = request.files['photo']
        if file.filename == '':
            return jsonify({'error': 'Nenhuma foto selecionada'}), 400
        
        if file and allowed_file(file.filename, ALLOWED_EXTENSIONS):
            # Gerar nome único para o arquivo
            filename = secure_filename(f"employee_{employee_id}_{int(datetime.now().timestamp())}.{file.filename.rsplit('.', 1)[1].lower()}")
            
            # Criar diretório se não existir
            upload_folder = os.path.join('uploads', 'employees')
            os.makedirs(upload_folder, exist_ok=True)
            
            file_path = os.path.join(upload_folder, filename)
            
            # Salvar arquivo
            file.save(file_path)
            
            # Redimensionar imagem
            try:
                with Image.open(file_path) as img:
                    # Redimensionar mantendo proporção
                    img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                    img.save(file_path, optimize=True, quality=85)
            except Exception as e:
                # Se falhar ao redimensionar, manter original
                pass
            
            # Remover foto anterior se existir
            if employee.photo_filename:
                old_path = os.path.join(upload_folder, employee.photo_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            # Atualizar banco de dados
            employee.photo_filename = filename
            employee.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'message': 'Foto enviada com sucesso',
                'filename': filename
            }), 200
        
        return jsonify({'error': 'Tipo de arquivo não permitido'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@employees_bp.route('/<int:employee_id>', methods=['DELETE'])
@api_login_required
@role_required('admin', 'rh')
def delete_employee(employee_id):
    """Deletar colaborador (soft delete)"""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({'error': 'Colaborador não encontrado'}), 404
        
        # Verificar permissões de restaurante
        if user_role == 'rh' and employee.restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada'}), 403
        
        # Soft delete
        employee.is_active = False
        employee.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Colaborador removido com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@employees_bp.route('/birthdays-this-month', methods=['GET'])
@api_login_required
def get_birthdays_this_month():
    """Obter aniversariantes do mês"""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        current_month = datetime.now().month
        
        # Query base
        query = Employee.query.filter(
            Employee.is_active == True,
            db.extract('month', Employee.birth_date) == current_month
        )
        
        # Filtrar por permissões
        if user_role not in ['admin', 'rh', 'marketing'] and user_restaurant_id:
            query = query.filter(Employee.restaurant_id == user_restaurant_id)
        
        employees = query.all()
        
        # Calcular idade e próximo aniversário
        current_year = datetime.now().year
        birthdays = []
        
        for employee in employees:
            birthday_this_year = employee.birth_date.replace(year=current_year)
            age = current_year - employee.birth_date.year
            
            birthdays.append({
                'employee': employee.to_dict(),
                'age': age,
                'birthday_this_year': birthday_this_year.isoformat()
            })
        
        # Ordenar por dia do aniversário
        birthdays.sort(key=lambda x: x['employee']['birth_date'][-2:])
        
        return jsonify({'birthdays': birthdays}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@employees_bp.route('/<int:employee_id>/upload-photo', methods=['POST'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def upload_employee_photo(employee_id):
    """Upload de foto para colaborador"""
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
        
        # Verificar se colaborador existe
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({'error': 'Colaborador não encontrado'}), 404
        
        # Verificar permissões
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        if user_role not in ['admin', 'rh'] and employee.restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada'}), 403
        
        try:
            # Criar pasta se não existir
            upload_folder = 'app/static/uploads/employees'
            os.makedirs(upload_folder, exist_ok=True)
            
            # Gerar nome seguro do arquivo
            filename = secure_filename(f"employee_{employee_id}_{datetime.now().timestamp()}.jpg")
            filepath = os.path.join(upload_folder, filename)
            
            # Redimensionar e otimizar imagem
            img = Image.open(file)
            
            # Converter para RGB se necessário (remove transparência, etc)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Redimensionar para 400x400 máximo
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            
            # Salvar com qualidade otimizada
            img.save(filepath, 'JPEG', quality=85, optimize=True)
            
            # Deletar foto antiga se existir
            if employee.photo_filename:
                old_path = os.path.join('app/static/uploads/employees', employee.photo_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            # Atualizar banco de dados
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
            return jsonify({'error': f'Erro ao processar imagem: {str(e)}'}), 500
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@employees_bp.route('/<int:employee_id>/photo', methods=['DELETE'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def delete_employee_photo(employee_id):
    """Deletar foto do colaborador"""
    try:
        # Verificar se colaborador existe
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({'error': 'Colaborador não encontrado'}), 404
        
        # Verificar permissões
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        if user_role not in ['admin', 'rh'] and employee.restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada'}), 403
        
        if employee.photo_filename:
            # Deletar arquivo
            old_path = os.path.join('app/static/uploads/employees', employee.photo_filename)
            if os.path.exists(old_path):
                os.remove(old_path)
            
            # Atualizar banco
            employee.photo_filename = None
            employee.updated_at = datetime.utcnow()
            db.session.commit()
        
        return jsonify({'message': 'Foto deletada com sucesso'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500