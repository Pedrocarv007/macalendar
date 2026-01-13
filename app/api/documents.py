"""
Rotas da API de Documentos
"""
from flask import Blueprint, request, jsonify, send_file, g, current_app, session
from app.extensions.database import db
from app.middleware.security import api_login_required, role_required
from app.models.document import Document
from app.services.documents.gererate_templates import generate_templates
from app.services.documents.download import get_single_document, get_bulk_zip
from app.services.documents.documents_crud import (
    list_documents as list_documents_service, 
    upload_document as upload_document_service,
    update_document as update_document_service,
    delete_document as delete_document_service
)

documents_bp = Blueprint('documents', __name__)

@documents_bp.route('', methods=['GET'])
@api_login_required
def get_documents():
    filters = request.args.to_dict()

    docs_query, stats = list_documents_service(session["user_role"], session["restaurant_id"], filters)

    return jsonify({
        'documents': [d.to_dict() for d in docs_query],
        'stats': stats
    }), 200

@documents_bp.route('', methods=['POST'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def create_document():
    """ create_document """
    if 'file' not in request.files:
        return jsonify({'error': 'Ficheiro ausente'}), 400
    try:
        doc = upload_document_service(request.files['file'], request.form, g.current_user_id, g.current_user_role, g.current_user_restaurant_id)
        return jsonify(doc.to_dict()), 201
    except (ValueError, PermissionError) as e:
        return jsonify({'error': str(e)}), 400
    

@documents_bp.route('/<int:document_id>', methods=['PUT'])
@api_login_required
def update_document(document_id):
    """ update_document """
    try:
        doc = Document.query.get_or_404(document_id)
        
        # 1. Tenta pegar dados do JSON (se vier com Header application/json)
        json_data = request.get_json(silent=True)
        
        # 2. Tenta pegar dados do Formulário (se vier como multipart/form-data)
        form_data = request.form.to_dict()
        
        # 3. Une os dois. O JSON tem prioridade, mas se for nulo, usa o Form
        data = json_data if json_data else form_data
        
        if not data:
            return jsonify({'error': 'Nenhum dado fornecido para atualização'}), 400
        
        # Chama a lógica do serviço enviando o dicionário unificado
        updated = update_document_service(
            doc, 
            data, 
            g.current_user_role, 
            g.current_user_restaurant_id
        )
        
        return jsonify(updated.to_dict()), 200

    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
@documents_bp.route('/<int:document_id>', methods=['DELETE'])
@api_login_required
def delete_document(document_id):
    try:
        doc = Document.query.get_or_404(document_id)
        delete_document_service(doc, session.get('user_role'), session.get('user_restaurant_id'))
        return jsonify({'message': 'Removido'}), 200
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
@documents_bp.route('/<int:document_id>/download', methods=['GET'])
@api_login_required
def download_document(document_id):
    """ download single document """
    try:
        document = Document.query.get_or_404(document_id)
        return get_single_document(
            document, 
            g.get('current_user_role'), 
            g.get('current_user_restaurant_id')
        )
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f"Erro interno: {str(e)}"}), 500

@documents_bp.route('/bulk-download', methods=['GET'])
@api_login_required
def bulk_download_documents():
    """ bulk_download_documents """
    try:
        ids_raw = request.args.get('ids', '')
        ids = [int(x) for x in ids_raw.split(',') if x.strip().isdigit()]
        
        if not ids:
            return jsonify({'error': 'IDs inválidos ou ausentes'}), 400

        documents = Document.query.filter(Document.id.in_(ids)).all()
        return get_bulk_zip(
            documents, 
            g.get('current_user_role'), 
            g.get('current_user_restaurant_id')
        )
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f"Erro no lote: {str(e)}"}), 500
@documents_bp.route('/generate-auto', methods=['POST'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def generate_document_auto():
    """Gerar documento automaticamente via templates"""
    try:
        # 1. Pega os dados
        data = request.get_json() or {}
        current_user_id = g.get('current_user_id')
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')

        return generate_templates(current_user_id, user_role, user_restaurant_id, data)

    except ValueError as e:
        # Se algum raise ValueError acontecer nas funções internas, cai aqui
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500