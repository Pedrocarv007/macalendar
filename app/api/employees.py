"""
Rotas da API de Colaboradores
"""
import os
import traceback
from datetime import datetime, date
import secrets
import string
import shutil

from flask import Blueprint, request, jsonify, g, current_app, url_for, Response
import io
import csv
from flask_jwt_extended import get_jwt_identity, get_jwt
from PIL import Image
from werkzeug.utils import secure_filename

from app.extensions.database import db
from app.middleware.security import api_login_required, role_required, allowed_file, validate_email
from app.models.employee import Employee
from app.models.workers import Worker
from app.models.restaurant import Restaurant
from app.models.activity_log import ActivityLog
from app.utils.email import send_email_async
from app.utils.notifications import notify_employee_change
from app.utils.registration_token import create_registration_token
import requests

employees_bp = Blueprint('employees', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def _normalize_birthday(original_date, target_year):
    """Ajusta data para lidar com aniversários em 29/02."""
    try:
        return original_date.replace(year=target_year)
    except ValueError:
        return original_date.replace(year=target_year, day=28)


def _save_worker_photo(file_storage, worker_id):
    """Salvar foto de worker retornando filename; usa uploads/workers com caminho absoluto."""
    timestamp = int(datetime.utcnow().timestamp() * 1000)
    filename = secure_filename(f"worker_{worker_id}_{timestamp}.png")
    base_dir = current_app.root_path  # .../app
    upload_dir = os.path.join(base_dir, 'static', 'uploads', 'workers')
    os.makedirs(upload_dir, exist_ok=True)
    upload_path = os.path.join(upload_dir, filename)

    img = Image.open(file_storage.stream)
    img.thumbnail((500, 500))
    img.save(upload_path, 'PNG')

    return filename

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
        worker_query = Worker.query
        
        # Filtrar por permissões
        if user_role in ['admin', 'rh', 'marketing']:
            # Pode ver todos os restaurantes
            if restaurant_id:
                query = query.filter(Employee.restaurant_id == restaurant_id)
                worker_query = worker_query.filter(Worker.restaurant_id == restaurant_id)
        else:
            # Só pode ver do próprio restaurante
            if user_restaurant_id:
                query = query.filter(Employee.restaurant_id == user_restaurant_id)
                worker_query = worker_query.filter(Worker.restaurant_id == user_restaurant_id)
            else:
                return jsonify({'employees': []}), 200
        
        employees = query.all()
        workers = worker_query.all()
        
        return jsonify({
            'employees': [employee.to_dict() for employee in employees],
            'workers': [worker.to_dict() for worker in workers]
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
        
        
        # Suportar tanto JSON quanto FormData
        if request.is_json:
            data = request.get_json()
        else:
            # FormData
            data = request.form.to_dict()
           

        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Validar dados obrigatórios
        required_fields = ['name', 'email', 'position', 'restaurant_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} é obrigatório'}), 400

        email = data['email'].strip().lower()
        if not validate_email(email):
            return jsonify({'error': 'Formato de email inválido'}), 400

        if Employee.query.filter_by(email=email).first():
            return jsonify({'error': 'Email já cadastrado'}), 409
        
        # Verificar se o usuário pode criar funcionário neste restaurante
        restaurant_id = int(data['restaurant_id'])
        if user_role not in ['admin', 'rh'] and restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada para este restaurante'}), 403
        
        # Verificar se restaurante existe
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            return jsonify({'error': 'Restaurante não encontrado'}), 404
        
        # Data de nascimento é opcional agora
        birth_date = None
        if data.get('birth_date'):
            try:
                birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400
        
        # Converter hire_date apenas se fornecido (opcional)
        hire_date = None
        if data.get('hire_date'):
            try:
                hire_date = datetime.strptime(data['hire_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de data de contratação inválido. Use YYYY-MM-DD'}), 400
        
        # Determinar role do colaborador
        valid_roles = current_app.config.get('VALID_ROLES', ['admin', 'rh', 'marketing', 'manager', 'employee'])
        requested_role = (data.get('role') or '').strip().lower() if data.get('role') else None
        role_to_set = 'employee'

        if requested_role:
            if requested_role not in valid_roles:
                return jsonify({'error': f"Role inválido. Deve ser um de: {', '.join(valid_roles)}"}), 400
            # Restrições: manager só pode criar 'employee'
            if user_role == 'manager' and requested_role != 'employee':
                return jsonify({'error': 'Gerentes só podem criar colaboradores com role "employee"'}), 403
            role_to_set = requested_role
        else:
            # Inferir role a partir de position/department (mapeamento atualizado)
            pos = (data.get('position') or '').strip().lower()
            dept = (data.get('department') or '').strip().lower()
            text = f"{pos} {dept}".replace('_', ' ')
            if any(k in text for k in ['rh', 'recursos humanos']):
                role_to_set = 'rh'
            elif any(k in text for k in ['gerente', 'sub gerente', 'gerente de turno', 'manager']):
                role_to_set = 'manager'
            elif any(k in text for k in ['rp', 'relações públicas', 'relacoes publicas', 'marketing']):
                role_to_set = 'marketing'
            elif any(k in text for k in ['admin', 'administração', 'administracao', 'desenvolvedor', 'developer', 'dev']):
                role_to_set = 'admin'
            else:
                role_to_set = 'employee'

            # Restrições para manager no papel inferido
            if user_role == 'manager' and role_to_set != 'employee':
                role_to_set = 'employee'

        # Criar colaborador
        employee = Employee(
            name=data['name'],
            email=email,
            phone=data.get('phone'),
            position=data['position'],
            department=data.get('department'),
            address=data.get('address'),
            birth_date=birth_date,
            hire_date=hire_date,
            restaurant_id=restaurant_id,
            notes=data.get('notes'),
            role=role_to_set
        )
        
        db.session.add(employee)
        db.session.flush()  # Obter ID antes de processar a foto

        # Gerar senha temporária forte e definir como senha inicial
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*()_+-=' 
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
        employee.set_password(temp_password)
        
        # Processar upload de foto se fornecido
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename, ALLOWED_EXTENSIONS):
                try:
                    # Salvar foto
                    timestamp = int(datetime.utcnow().timestamp() * 1000)  # em milissegundos
                    filename = secure_filename(f"employee_{employee.id}_{timestamp}.png")
                    
                    # Usar caminho absoluto baseado no diretório da aplicação (pasta 'app')
                    base_dir = os.path.dirname(os.path.abspath(__file__))  # .../app/api
                    app_dir = os.path.normpath(os.path.join(base_dir, '..'))  # .../app
                    upload_dir = os.path.join(app_dir, 'static', 'uploads', 'employees')
                    upload_path = os.path.join(upload_dir, filename)
                    
                    # Garantir que o diretório existe
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Redimensionar imagem
                    img = Image.open(file.stream)
                    img.thumbnail((500, 500))
                    img.save(upload_path, 'PNG')
                    
                    
                    # Atualizar URL da foto
                    employee.photo_url = f'/uploads/employees/{filename}'
                except Exception as e:
                    print(f'Erro ao processar foto: {str(e)}')
                    # Continuar mesmo se falhar a foto
        
        # Registrar atividade
        current_user = Employee.query.get(current_user_id)
        ActivityLog.log_activity(
            activity_type='employee_created',
            description=f'Novo colaborador adicionado: {employee.name} por {current_user.name if current_user else "Sistema"}',
            user_id=current_user_id,
            restaurant_id=restaurant_id,
            target_id=employee.id,
            target_type='employee'
        )
        
        db.session.commit()

        # Enviar email de boas-vindas com credenciais temporárias
        try:
            login_url = url_for('auth_web.login', _external=True)
            html_content = f"""
                <!DOCTYPE html>
                <html lang="pt-BR">
                    <head>
                        <meta charset="UTF-8">
                        <title>Teste SMTP | MAC Calendar</title>
                        <style>  
                            body {{
                                margin: 0;
                                padding: 0;
                                background: #f5f7fb;
                                color: #243447;
                                font-family: 'Segoe UI', Arial, sans-serif;
                            }}
                            .container {{
                                max-width: 640px;
                                margin: 0 auto;
                                padding: 32px 24px;
                            }}
                            .card {{
                                background: #ffffff;
                                border: 1px solid #e5e9f2;
                                border-radius: 12px;
                                box-shadow: 0 8px 20px rgba(18, 38, 63, 0.08);
                                padding: 32px;
                            }}
                            .brand {{
                                text-align: center;
                                margin-bottom: 24px;
                            }}
                            .brand h1 {{
                                margin: 8px 0 0 0;
                                font-size: 24px;
                                color: #0f6ddf;
                            }}
                            .badge {{
                                display: inline-block;
                                background: #e8f1ff;
                                color: #0f6ddf;
                                padding: 6px 12px;
                                border-radius: 999px;
                                font-weight: 600;
                                font-size: 12px;
                                letter-spacing: 0.5px;
                            }}
                            h2 {{
                                color: #141c2c;
                                margin: 0 0 8px 0;
                                font-size: 20px;
                            }}
                            p {{
                                margin: 0 0 12px 0;
                                line-height: 1.6;
                            }}
                            .list {{
                                margin: 16px 0;
                                padding-left: 18px;
                            }}
                            .list li {{
                                margin-bottom: 10px;
                            }}
                            .panel {{
                                background: #f8fafc;
                                border: 1px solid #e5e9f2;
                                border-radius: 10px;
                                padding: 14px 16px;
                                margin: 16px 0;
                                font-family: 'SFMono-Regular', Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
                                font-size: 13px;
                                color: #1f2937;
                            }}
                            .cta {{
                                text-align: center;
                                margin: 24px 0 12px 0;
                            }}
                            .cta a {{
                                display: inline-block;
                                background: #0f6ddf;
                                color: #ffffff;
                                padding: 12px 20px;
                                border-radius: 8px;
                                text-decoration: none;
                                font-weight: 600;
                            }}
                            .footer {{
                                text-align: center;
                                color: #6b778c;
                                font-size: 12px;
                                margin-top: 16px;
                                line-height: 1.4;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="card">
                                <div class="brand">
                                    <span class="badge">MAC Calendar</span>
                                    <h1>Bem vindo {employee.name}!</h1>
                                </div>
                                <h2>Credenciais Temporárias</h2>
                                <p>Olá, {employee.name}! Aqui estão suas credenciais temporárias para acessar o MAC Calendar.</p>
                                <div class="panel">
                                    <strong>Checklist rápido:</strong><br>
                                    • Entre em www.thecarv.com/mac<br>
                                    • Utilize o email: {employee.email} e a senha: {temp_password} temporária fornecida.<br>
                                    • Mude a senha no primeiro acesso para garantir a segurança da sua conta.
                                </div>
                                <h2>Próximos passos sugeridos</h2>
                                <div class="cta">
                                    <a href="{login_url}" target="_blank" rel="noopener">Acessar MAC Calendar</a>
                                </div>
                                <p>Qualquer dúvida, responda este e-mail e nossa equipe ajudará você a finalizar a configuração.</p>
                                <div class="footer">
                                    MAC Calendar · Thecarv Sistemas<br>
                                    <p>Qualquer dúvida, contate o RH.</p>
                                    &copy; {datetime.now().year} Thecarv Sistemas. Todos os direitos reservados.
                                </div>
                            </div>
                        </div>
                    </body>
                </html>
                """
            send_email_async(
                to=employee.email,
                subject='Bem-vindo(a) ao MAC Calendar - Credenciais temporárias',
                html=html_content,
                mail_profile="noreply"
            )
        except Exception as e:
            current_app.logger.exception(f'Falha ao enviar email de boas-vindas: {e}')

        # Notificar criação
        try:
            notify_employee_change('criado', employee, current_user)
        except Exception:
            pass
        
        # Enviar dados para SSO central se configurado
        sso_url = "https://www.thecarv.com/callback/register"
        token = create_registration_token(email=employee.email, password=temp_password, status='active')

        try:
            sso_response = requests.post(sso_url, json=token, timeout=5)
            sso_response.raise_for_status()
            
        except Exception as e:
            current_app.logger.error(f"Erro ao enviar para SSO central: {e}")
        
        return jsonify({
            'message': 'Colaborador criado com sucesso',
            'employee': employee.to_dict(),
        }), 201
        
    except Exception as e:
        db.session.rollback()
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
        
       
        
        # Suportar tanto JSON quanto FormData
        if request.is_json:
            data = request.get_json()
        else:
            # FormData (incluindo upload de foto)
            data = request.form.to_dict()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Atualizar campos
        if 'name' in data:
            employee.name = data['name']
        if 'email' in data:
            employee.email = data['email']
        if 'phone' in data:
            employee.phone = data['phone']
        position_changed = False
        department_changed = False
        if 'position' in data:
            employee.position = data['position']
            position_changed = True
        if 'department' in data:
            employee.department = data['department']
            department_changed = True
        if 'address' in data:
            employee.address = data['address']
        if 'role' in data and data['role']:
            requested_role = data['role'].strip().lower()
            valid_roles = current_app.config.get('VALID_ROLES')
            if requested_role not in valid_roles:
                return jsonify({'error': f"Role inválido. Deve ser um de: {', '.join(valid_roles)}"}), 400
            if user_role == 'manager' and requested_role != 'employee':
                return jsonify({'error': 'Gerentes só podem definir role "employee"'}), 403
            employee.role = requested_role
        elif position_changed or department_changed:
            # Inferir novo role automaticamente quando cargo/departamento mudarem
            pos = (employee.position or '').strip().lower()
            dept = (employee.department or '').strip().lower()
            text = f"{pos} {dept}".replace('_', ' ')
            inferred_role = 'employee'
            if any(k in text for k in ['rh', 'recursos humanos']):
                inferred_role = 'rh'
            elif any(k in text for k in ['gerente', 'sub gerente', 'gerente de turno', 'manager']):
                inferred_role = 'manager'
            elif any(k in text for k in ['rp', 'relações públicas', 'relacoes publicas', 'marketing']):
                inferred_role = 'marketing'
            elif any(k in text for k in ['admin', 'administração', 'administracao', 'desenvolvedor', 'developer', 'dev']):
                inferred_role = 'admin'
            # Restrições: manager não pode elevar
            if user_role == 'manager' and inferred_role != 'employee':
                inferred_role = 'employee'
            employee.role = inferred_role
        if 'birth_date' in data and data['birth_date']:
            employee.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
        if 'hire_date' in data and data['hire_date']:
            employee.hire_date = datetime.strptime(data['hire_date'], '%Y-%m-%d').date()
        if 'is_active' in data:
            # Converter string para boolean
            is_active_value = data['is_active']
            if isinstance(is_active_value, str):
                employee.is_active = is_active_value.lower() in ['true', '1', 'yes', 'on']
            else:
                employee.is_active = bool(is_active_value)
        if 'notes' in data:
            employee.notes = data['notes']
        if 'restaurant_id' in data:
            # Validar restaurante
            restaurant = Restaurant.query.get(int(data['restaurant_id']))
            if not restaurant:
                return jsonify({'error': 'Restaurante não encontrado'}), 404
            employee.restaurant_id = int(data['restaurant_id'])
        
        # Processar upload de foto se fornecido
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename, ALLOWED_EXTENSIONS):
                try:
                    # Salvar foto
                    timestamp = int(datetime.utcnow().timestamp() * 1000)  # em milissegundos
                    filename = secure_filename(f"employee_{employee_id}_{timestamp}.png")
                    
                    # Usar caminho absoluto baseado no diretório da aplicação (pasta 'app')
                    base_dir = os.path.dirname(os.path.abspath(__file__))  # .../app/api
                    app_dir = os.path.normpath(os.path.join(base_dir, '..'))  # .../app
                    upload_dir = os.path.join(app_dir, 'static', 'uploads', 'employees')
                    upload_path = os.path.join(upload_dir, filename)
                    
                    # Garantir que o diretório existe
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Redimensionar imagem
                    img = Image.open(file.stream)
                    img.thumbnail((500, 500))
                    img.save(upload_path, 'PNG')

                    
                    # Atualizar URL da foto
                    employee.photo_url = f'/uploads/employees/{filename}'
                except Exception as e:
                    print(f'Erro ao processar foto: {str(e)}')
                    import traceback
                    traceback.print_exc()
                    # Continuar mesmo se falhar a foto
        
        employee.updated_at = datetime.utcnow()
        db.session.commit()

        # Notificar atualização
        try:
            actor = Employee.query.get(g.get('current_user_id'))
            notify_employee_change('atualizado', employee, actor)
        except Exception:
            pass
        
        return jsonify({
            'message': 'Colaborador atualizado com sucesso',
            'employee': employee.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(traceback.format_exc())
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

        # Notificar desativação
        try:
            actor = Employee.query.get(g.get('current_user_id'))
            notify_employee_change('desativado', employee, actor)
        except Exception:
            pass
        
        return jsonify({'message': 'Colaborador removido com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


# ----------------------
# Rotas para Workers (somente para templates automáticos)
# ----------------------

@employees_bp.route('/workers', methods=['GET'])
@api_login_required
def get_workers():
    """Listar workers (não usuários), filtrando por restaurante e ativo."""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        restaurant_id = request.args.get('restaurant_id', type=int)

        query = Worker.query.filter(Worker.is_active == True)
        if user_role not in ['admin', 'rh', 'marketing']:
            if user_restaurant_id:
                query = query.filter(Worker.restaurant_id == user_restaurant_id)
            else:
                return jsonify({'workers': []}), 200
        elif restaurant_id:
            query = query.filter(Worker.restaurant_id == restaurant_id)

        workers = query.order_by(Worker.name.asc()).all()
        return jsonify({'workers': [w.to_dict() for w in workers]}), 200
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@employees_bp.route('/workers', methods=['POST'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def create_worker():
    """Criar worker (apenas nome, datas e foto)."""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')

        data = request.get_json() if request.is_json else request.form.to_dict()
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        required_fields = ['name', 'birth_date', 'restaurant_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} é obrigatório'}), 400

        restaurant_id = int(data['restaurant_id'])
        if user_role not in ['admin', 'rh'] and restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada para este restaurante'}), 403

        # Validar datas
        try:
            birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de birth_date inválido. Use YYYY-MM-DD'}), 400

        hire_date = None
        if data.get('hire_date'):
            try:
                hire_date = datetime.strptime(data['hire_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de hire_date inválido. Use YYYY-MM-DD'}), 400

        worker = Worker(
            name=data['name'],
            birth_date=birth_date,
            hire_date=hire_date,
            restaurant_id=restaurant_id,
            is_active=True
        )

        db.session.add(worker)
        db.session.flush()  # obter ID

        # Foto opcional
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename, ALLOWED_EXTENSIONS):
                filename = _save_worker_photo(file, worker.id)
                worker.photo_filename = filename

        db.session.commit()
        return jsonify({'message': 'Worker criado com sucesso', 'worker': worker.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@employees_bp.route('/workers/<int:worker_id>', methods=['PUT'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def update_worker(worker_id):
    """Editar worker."""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')

        worker = Worker.query.get(worker_id)
        if not worker or not worker.is_active:
            return jsonify({'error': 'Worker não encontrado'}), 404

        if user_role not in ['admin', 'rh'] and worker.restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada'}), 403

        data = request.get_json() if request.is_json else request.form.to_dict()
        if not data and 'photo' not in request.files:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        if 'name' in data:
            worker.name = data['name']
        if 'birth_date' in data and data['birth_date']:
            try:
                worker.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de birth_date inválido. Use YYYY-MM-DD'}), 400
        if 'hire_date' in data:
            if data['hire_date']:
                try:
                    worker.hire_date = datetime.strptime(data['hire_date'], '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': 'Formato de hire_date inválido. Use YYYY-MM-DD'}), 400
            else:
                worker.hire_date = None
        if 'restaurant_id' in data:
            new_restaurant_id = int(data['restaurant_id'])
            if user_role not in ['admin', 'rh'] and new_restaurant_id != user_restaurant_id:
                return jsonify({'error': 'Permissão negada para este restaurante'}), 403
            worker.restaurant_id = new_restaurant_id

        # Atualizar foto
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename, ALLOWED_EXTENSIONS):
                # remover foto anterior
                if worker.photo_filename:
                    old_path = os.path.join(current_app.root_path, 'static', 'uploads', 'workers', worker.photo_filename)
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except Exception:
                            pass
                filename = _save_worker_photo(file, worker.id)
                worker.photo_filename = filename

        worker.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Worker atualizado com sucesso', 'worker': worker.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@employees_bp.route('/workers/<int:worker_id>', methods=['DELETE'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def delete_worker(worker_id):
    """Remover worker (soft delete)."""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')

        worker = Worker.query.get(worker_id)
        if not worker or not worker.is_active:
            return jsonify({'error': 'Worker não encontrado'}), 404

        if user_role not in ['admin', 'rh'] and worker.restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada'}), 403

        worker.is_active = False
        worker.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Worker removido com sucesso'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@employees_bp.route('/workers/<int:worker_id>/convert', methods=['POST'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def convert_worker_to_employee(worker_id):
    """Converter um worker em employee, enviando OTP por email se for novo."""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')

        worker = Worker.query.get(worker_id)
        if not worker or not worker.is_active:
            return jsonify({'error': 'Worker não encontrado'}), 404

        data = request.get_json() if request.is_json else request.form.to_dict()
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        email = (data.get('email') or '').strip().lower()
        if not email:
            return jsonify({'error': 'Email é obrigatório para converter'}), 400
        if not validate_email(email):
            return jsonify({'error': 'Formato de email inválido'}), 400
        if Employee.query.filter_by(email=email).first():
            return jsonify({'error': 'Email já cadastrado em employees'}), 409

        # Permissão por restaurante
        target_restaurant_id = int(data.get('restaurant_id') or worker.restaurant_id)
        if user_role not in ['admin', 'rh'] and target_restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada para este restaurante'}), 403

        position = data.get('position') or 'Colaborador'
        hire_date = worker.hire_date
        if data.get('hire_date'):
            try:
                hire_date = datetime.strptime(data['hire_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de hire_date inválido. Use YYYY-MM-DD'}), 400
        birth_date = worker.birth_date
        if data.get('birth_date'):
            try:
                birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de birth_date inválido. Use YYYY-MM-DD'}), 400

        employee = Employee(
            name=worker.name,
            email=email,
            phone=data.get('phone'),
            position=position,
            department=data.get('department'),
            address=data.get('address'),
            birth_date=birth_date,
            hire_date=hire_date,
            restaurant_id=target_restaurant_id,
            notes=data.get('notes'),
            role='employee'
        )

        db.session.add(employee)
        db.session.flush()

        # Senha temporária
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*()_+-='
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
        employee.set_password(temp_password)

        # Copiar foto do worker para pasta de employees se existir
        if worker.photo_filename:
            try:
                src = os.path.join(current_app.root_path, 'static', 'uploads', 'workers', worker.photo_filename)
                if os.path.exists(src):
                    ext = os.path.splitext(worker.photo_filename)[1] or '.png'
                    dest_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'employees')
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_filename = secure_filename(f"employee_{employee.id}_{int(datetime.utcnow().timestamp()*1000)}{ext}")
                    dest_path = os.path.join(dest_dir, dest_filename)
                    shutil.copyfile(src, dest_path)
                    employee.photo_filename = dest_filename
            except Exception as copy_err:
                current_app.logger.warning(f'Falha ao copiar foto de worker: {copy_err}')

        # Marcar worker como inativo
        worker.is_active = False
        worker.updated_at = datetime.utcnow()

        db.session.commit()

        # Enviar email com OTP
        try:
            login_url = url_for('auth_web.login', _external=True)
            html_content = f"""
                <h3>Bem-vindo ao MAC Calendar</h3>
                <p>Olá {employee.name}, sua conta foi criada.</p>
                <p><strong>Email:</strong> {employee.email}<br>
                <strong>Senha temporária (OTP):</strong> {temp_password}</p>
                <p>Faça login e altere sua senha: <a href="{login_url}">{login_url}</a></p>
            """
            send_email_async(
                to=employee.email,
                subject='Sua conta MAC Calendar',
                html=html_content,
                mail_profile="noreply"
            )
        except Exception as mail_err:
            current_app.logger.warning(f'Falha ao enviar email de OTP: {mail_err}')

        return jsonify({'message': 'Worker convertido para employee com sucesso', 'employee': employee.to_dict()}), 201
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
            birthday_this_year = _normalize_birthday(employee.birth_date, current_year)
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