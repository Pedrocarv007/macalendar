"""
Rotas da API de Documentos
"""
import os
import traceback
from datetime import datetime
from datetime import date as date_module
from flask import Blueprint, request, jsonify, send_file, g
from flask_jwt_extended import get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename

from app.extensions.database import db
from app.middleware.security import api_login_required, role_required
from app.models.document import Document
from app.models.employee import Employee
from app.models.restaurant import Restaurant
from app.models.activity_log import ActivityLog
from app.utils.document_generator import DocumentGenerator

documents_bp = Blueprint('documents', __name__)

@documents_bp.route('', methods=['GET'])
@api_login_required
def get_documents():
    """Obter lista de documentos"""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        # Parâmetros de filtro
        restaurant_id = request.args.get('restaurant_id', type=int)
        document_type = request.args.get('document_type')
        employee_id = request.args.get('employee_id', type=int)
        
        # Query base
        query = Document.query
        
        # Filtrar por tipo
        if document_type:
            query = query.filter(Document.document_type == document_type)
        
        # Filtrar por funcionário
        if employee_id:
            query = query.filter(Document.employee_id == employee_id)
        
        # Filtrar por permissões
        if user_role in ['admin', 'rh', 'marketing']:
            # Pode ver todos os restaurantes
            if restaurant_id:
                query = query.filter(Document.restaurant_id == restaurant_id)
        else:
            # Só pode ver do próprio restaurante
            if user_restaurant_id:
                query = query.filter(Document.restaurant_id == user_restaurant_id)
            else:
                return jsonify({'documents': []}), 200
        
        documents = query.order_by(Document.created_at.desc()).all()
        
        return jsonify({
            'documents': [doc.to_dict() for doc in documents]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@documents_bp.route('', methods=['POST'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def create_document():
    """Criar novo documento com upload de arquivo"""
    try:
        current_user_id = g.get('current_user_id')
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        # Obter dados do usuário logado (agora é um employee)
        current_user = Employee.query.get(current_user_id)

        # Validar arquivo
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo foi enviado'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Arquivo não selecionado'}), 400

        # Dados do formulário
        name = request.form.get('name') or file.filename
        category = request.form.get('category')
        employee_id = request.form.get('employee_id', type=int)
        description = request.form.get('description')
        tags = request.form.get('tags')
        restaurant_id = request.form.get('restaurant_id', type=int)
        is_public = request.form.get('is_public') == 'true'
        
        if not restaurant_id:
            return jsonify({'error': 'Restaurant ID é obrigatório'}), 400
        
        if not category:
            return jsonify({'error': 'Categoria é obrigatória'}), 400
        
        # Se employee_id não foi fornecido, usar o do user logado
        if not employee_id:
            if current_user:
                employee_id = current_user.id
                print(f"DEBUG - Usando employee_id do user logado: {employee_id}")
            else:
                return jsonify({'error': 'Colaborador é obrigatório'}), 400
        
        # Verificar se colaborador existe
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({'error': 'Colaborador não encontrado'}), 404
        
        # Verificar se colaborador pertence ao restaurante
        if employee.restaurant_id != restaurant_id:
            return jsonify({'error': 'Colaborador não pertence a este restaurante'}), 400
        
        # Verificar permissões
        if user_role not in ['admin', 'rh'] and restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada para este restaurante'}), 403
        
        # Verificar se restaurante existe
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            return jsonify({'error': 'Restaurante não encontrado'}), 404
        
        # Criar diretório de upload se não existir
        upload_folder = os.path.join('uploads', 'documents', str(restaurant_id))
        os.makedirs(upload_folder, exist_ok=True)
        
        # Gerar nome de arquivo seguro
        filename = secure_filename(f"{int(datetime.now().timestamp())}_{file.filename}")
        file_path = os.path.join(upload_folder, filename)
        
        # Salvar arquivo
        file.save(file_path)
        
        # Obter tamanho do arquivo
        file_size = os.path.getsize(file_path)
        
        # Criar documento no banco de dados
        document = Document(
            title=name,
            document_type=category,
            template_name=category,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            restaurant_id=restaurant_id,
            employee_id=employee_id,
            created_by=current_user_id,
            description=description,
            tags=tags,
            is_public=is_public,
            status='uploaded'
        )
        
        db.session.add(document)
        
        # Registrar atividade
        current_user = Employee.query.get(current_user_id)
        ActivityLog.log_activity(
            activity_type='document_uploaded',
            description=f'Documento enviado: {name} por {current_user.name if current_user else "Sistema"}',
            user_id=current_user_id,
            restaurant_id=restaurant_id,
            target_id=document.id,
            target_type='document'
        )
        
        db.session.commit()
        
        return jsonify({
            'message': 'Documento enviado com sucesso',
            'document': document.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@documents_bp.route('/<int:document_id>', methods=['PUT'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def update_document(document_id):
    """Atualizar documento"""
    try:
        # claims via g
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        document = Document.query.get(document_id)
        if not document:
            return jsonify({'error': 'Documento não encontrado'}), 404
        
        # Verificar permissões
        if user_role not in ['admin', 'rh']:
            if document.restaurant_id != user_restaurant_id:
                return jsonify({'error': 'Permissão negada'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Atualizar campos
        if 'title' in data:
            document.title = data['title']
        if 'content' in data:
            document.content = data['content']
        if 'template_name' in data:
            document.template_name = data['template_name']
        if 'status' in data:
            valid_statuses = ['draft', 'generated', 'sent']
            if data['status'] in valid_statuses:
                document.status = data['status']
        
        document.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Documento atualizado com sucesso',
            'document': document.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@documents_bp.route('/<int:document_id>', methods=['DELETE'])
@api_login_required
@role_required('admin', 'rh')
def delete_document(document_id):
    """Deletar documento"""
    try:
        # claims via g
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        document = Document.query.get(document_id)
        if not document:
            return jsonify({'error': 'Documento não encontrado'}), 404
        
        # Verificar permissões
        if user_role == 'rh' and document.restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada'}), 403
        
        # Remover arquivo físico se existir
        if document.file_path and os.path.exists(document.file_path):
            try:
                os.remove(document.file_path)
            except Exception as e:
                print(f"Erro ao remover arquivo: {e}")
        
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({'message': 'Documento removido com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@documents_bp.route('/<int:document_id>/download', methods=['GET'])
@api_login_required
def download_document(document_id):
    """Download do documento"""
    try:
        # claims via g
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        document = Document.query.get(document_id)
        if not document:
            return jsonify({'error': 'Documento não encontrado'}), 404
        
        # Verificar permissões
        if user_role not in ['admin', 'rh', 'marketing']:
            if document.restaurant_id != user_restaurant_id:
                return jsonify({'error': 'Permissão negada'}), 403
        
        # Verificar se arquivo existe
        if not document.file_path or not os.path.exists(document.file_path):
            return jsonify({'error': 'Arquivo não encontrado'}), 404
        
        return send_file(
            document.file_path,
            as_attachment=True,
            download_name=document.filename or f'documento_{document_id}.pdf'
        )
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@documents_bp.route('/templates', methods=['GET'])
@api_login_required
def get_templates():
    """Obter lista de templates disponíveis"""
    try:
        # Templates predefinidos (posteriormente será dinâmico)
        templates = {
            'birthday': [
                {
                    'name': 'birthday_classic',
                    'title': 'Aniversário Clássico',
                    'description': 'Template tradicional para parabéns de aniversário',
                    'preview': '/static/templates/birthday_classic_preview.png'
                },
                {
                    'name': 'birthday_modern',
                    'title': 'Aniversário Moderno',
                    'description': 'Template moderno e colorido para aniversários',
                    'preview': '/static/templates/birthday_modern_preview.png'
                }
            ],
            'praise': [
                {
                    'name': 'praise_certificate',
                    'title': 'Certificado de Elogio',
                    'description': 'Template formal para certificados de reconhecimento',
                    'preview': '/static/templates/praise_certificate_preview.png'
                },
                {
                    'name': 'praise_card',
                    'title': 'Cartão de Elogio',
                    'description': 'Template simples para cartões de elogio',
                    'preview': '/static/templates/praise_card_preview.png'
                }
            ]
        }
        
        return jsonify({'templates': templates}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@documents_bp.route('/generate', methods=['POST'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def generate_document():
    """Gerar documento PDF usando template"""
    try:
        current_user_id = g.get('current_user_id')
        # claims via g
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        document_id = data.get('document_id')
        if not document_id:
            return jsonify({'error': 'ID do documento é obrigatório'}), 400
        
        document = Document.query.get(document_id)
        if not document:
            return jsonify({'error': 'Documento não encontrado'}), 404
        
        # Verificar permissões
        if user_role not in ['admin', 'rh']:
            if document.restaurant_id != user_restaurant_id:
                return jsonify({'error': 'Permissão negada'}), 403
        
        # Aqui seria implementada a lógica de geração do PDF
        # Por enquanto, simular a geração
        
        # Criar diretório se não existir
        documents_folder = os.path.join('uploads', 'documents')
        os.makedirs(documents_folder, exist_ok=True)
        
        # Simular geração do arquivo
        filename = f"document_{document_id}_{int(datetime.now().timestamp())}.pdf"
        file_path = os.path.join(documents_folder, filename)
        
        # Aqui seria chamada a função de geração real do PDF
        # generate_pdf_from_template(document, file_path)
        
        # Por enquanto, criar arquivo vazio para teste
        with open(file_path, 'w') as f:
            f.write("PDF gerado")
        
        # Atualizar documento
        document.filename = filename
        document.file_path = file_path
        document.file_size = os.path.getsize(file_path)
        document.status = 'generated'
        document.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Documento gerado com sucesso',
            'document': document.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@documents_bp.route('/generate-auto', methods=['POST'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def generate_document_auto():
    """Gerar documento automaticamente (cartão de boas-vindas, aniversário) - APENAS nome, data e foto"""
    try:
        current_user_id = g.get('current_user_id')
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        data = request.get_json() or {}
        
        # Parâmetros
        document_type = data.get('document_type')  # 'bem_vindo', 'aniversario'
        try:
            employee_id = int(data.get('employee_id', 0)) if data.get('employee_id') else None
            restaurant_id = int(data.get('restaurant_id', 0)) if data.get('restaurant_id') else None
        except (ValueError, TypeError):
            return jsonify({'error': 'Employee ID e Restaurant ID devem ser números'}), 400
        
        if not document_type:
            return jsonify({'error': 'Tipo de documento é obrigatório'}), 400
        
        if not employee_id or not restaurant_id:
            return jsonify({'error': 'Employee ID e Restaurant ID são obrigatórios'}), 400
        
        # Verificar permissões
        if user_role not in ['admin', 'rh'] and restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada para este restaurante'}), 403
        
        # Obter dados do colaborador
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({'error': 'Colaborador não encontrado'}), 404
        
        if employee.restaurant_id != restaurant_id:
            return jsonify({'error': 'Colaborador não pertence a este restaurante'}), 400
        
        # Verificar restaurante
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            return jsonify({'error': 'Restaurante não encontrado'}), 404
        
        # Gerar documento
        generator = DocumentGenerator()
        photo_path = None
        
        # Obter caminho da foto se existir
        if employee.photo_filename:
            photo_path = os.path.join('app/static/uploads/employees', employee.photo_filename)
        
        try:
            if document_type.lower() == 'bem_vindo':
                file_path, filename = generator.generate_welcome_card(
                    employee_name=employee.name,
                    employee_photo_path=photo_path,
                    restaurant_name=restaurant.name
                )
                doc_category = 'Boas-vindas'
            
            elif document_type.lower() == 'aniversario':
                # Usar data de aniversário no ano atual, não o ano de nascimento

                birth_date_current_year = employee.birth_date
                if birth_date_current_year:
                    try:
                        birth_date_current_year = employee.birth_date.replace(year=date_module.today().year)
                    except ValueError:
                        # Lidar com 29/02 em anos não bissextos
                        birth_date_current_year = employee.birth_date.replace(year=date_module.today().year, day=28)
                
                file_path, filename = generator.generate_birthday_card(
                    employee_name=employee.name,
                    birth_date=birth_date_current_year,
                    employee_photo_path=photo_path
                )
                doc_category = 'Aniversário'
            
            else:
                return jsonify({'error': f'Tipo de documento inválido: {document_type}. Use: bem_vindo, aniversario'}), 400
            
        except Exception as e:
            return jsonify({'error': f'Erro ao gerar documento: {str(e)}'}), 500
        
        # Obter tamanho do arquivo
        file_size = os.path.getsize(file_path)
        
        # Criar documento no banco de dados
        document = Document(
            title=f'Cartão - {employee.name}',
            document_type=doc_category,
            template_name=document_type,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            restaurant_id=restaurant_id,
            employee_id=employee_id,
            created_by=current_user_id,
            description=f'Documento gerado automaticamente - {document_type}',
            tags=f'{document_type},{employee.name}',
            is_public=False,
            status='generated'
        )
        
        db.session.add(document)
        db.session.commit()
        
        return jsonify({
            'message': 'Documento gerado com sucesso',
            'document': document.to_dict(),
            'file_path': file_path
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao gerar documento: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
