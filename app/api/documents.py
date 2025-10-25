"""
Rotas da API de Documentos
"""
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime
import os
from app.extensions.database import db
from app.models.document import Document
from app.models.employee import Employee
from app.models.restaurant import Restaurant
from app.middleware.security import role_required

documents_bp = Blueprint('documents', __name__)

@documents_bp.route('', methods=['GET'])
@jwt_required()
def get_documents():
    """Obter lista de documentos"""
    try:
        claims = get_jwt()
        user_role = claims.get('role')
        user_restaurant_id = claims.get('restaurant_id')
        
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
@jwt_required()
@role_required('admin', 'rh', 'manager')
def create_document():
    """Criar novo documento"""
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        user_role = claims.get('role')
        user_restaurant_id = claims.get('restaurant_id')
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Validar dados obrigatórios
        required_fields = ['title', 'document_type', 'template_name', 'employee_id', 'restaurant_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} é obrigatório'}), 400
        
        # Verificar permissões
        restaurant_id = data['restaurant_id']
        if user_role not in ['admin', 'rh'] and restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada para este restaurante'}), 403
        
        # Verificar se funcionário existe
        employee = Employee.query.get(data['employee_id'])
        if not employee:
            return jsonify({'error': 'Funcionário não encontrado'}), 404
        
        # Verificar se funcionário pertence ao restaurante
        if employee.restaurant_id != restaurant_id:
            return jsonify({'error': 'Funcionário não pertence a este restaurante'}), 400
        
        # Verificar se restaurante existe
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            return jsonify({'error': 'Restaurante não encontrado'}), 404
        
        # Criar documento
        document = Document(
            title=data['title'],
            document_type=data['document_type'],
            template_name=data['template_name'],
            employee_id=data['employee_id'],
            restaurant_id=restaurant_id,
            created_by=current_user_id,
            content=data.get('content'),
            status='draft'
        )
        
        db.session.add(document)
        db.session.commit()
        
        return jsonify({
            'message': 'Documento criado com sucesso',
            'document': document.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@documents_bp.route('/<int:document_id>', methods=['PUT'])
@jwt_required()
@role_required('admin', 'rh', 'manager')
def update_document(document_id):
    """Atualizar documento"""
    try:
        claims = get_jwt()
        user_role = claims.get('role')
        user_restaurant_id = claims.get('restaurant_id')
        
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
@jwt_required()
@role_required('admin', 'rh')
def delete_document(document_id):
    """Deletar documento"""
    try:
        claims = get_jwt()
        user_role = claims.get('role')
        user_restaurant_id = claims.get('restaurant_id')
        
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
@jwt_required()
def download_document(document_id):
    """Download do documento"""
    try:
        claims = get_jwt()
        user_role = claims.get('role')
        user_restaurant_id = claims.get('restaurant_id')
        
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
@jwt_required()
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
@jwt_required()
@role_required('admin', 'rh', 'manager')
def generate_document():
    """Gerar documento PDF usando template"""
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        user_role = claims.get('role')
        user_restaurant_id = claims.get('restaurant_id')
        
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