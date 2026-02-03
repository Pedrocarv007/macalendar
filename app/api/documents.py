from flask import Blueprint, request, jsonify, g
from app.middleware.security import api_login_required
from app.services.documents.documents_services import DocumentService 

documents_bp = Blueprint('documents', __name__)

# Helper para instanciar o serviço com o contexto do utilizador atual
def get_service():
    return DocumentService(
        user_id=g.get('current_user_id'),
        user_role=g.get('current_user_role'),
        user_restaurant_id=g.get('current_user_restaurant_id')
    )

@documents_bp.route('', methods=['GET'])
@api_login_required
def get_documents():
    service = get_service()
    result = service.list(request.args.to_dict())
    return jsonify(result), 200

@documents_bp.route('', methods=['POST'])
@api_login_required
def create_document():
    if 'file' not in request.files:
        return jsonify({'error': 'Ficheiro ausente'}), 400
    
    try:
        service = get_service()
        doc = service.upload(request.files['file'], request.form)
        return jsonify(doc.to_dict()), 201
    except (ValueError, PermissionError) as e:
        return jsonify({'error': str(e)}), 400

@documents_bp.route('/<int:document_id>', methods=['PUT'])
@api_login_required
def update_document(document_id):
    try:
        service = get_service()
        data = request.get_json(silent=True) or request.form.to_dict()
        
        updated_doc = service.update(document_id, data)
        return jsonify(updated_doc.to_dict()), 200
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': f'Erro: {str(e)}'}), 500

@documents_bp.route('/<int:document_id>', methods=['DELETE'])
@api_login_required
def delete_document(document_id):
    try:
        service = get_service()
        service.delete(document_id)
        return jsonify({'message': 'Removido com sucesso'}), 200
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403

@documents_bp.route('/<int:document_id>/download', methods=['GET'])
@api_login_required
def download_document(document_id):
    try:
        service = get_service()
        return service.download_single(document_id)
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404

@documents_bp.route('/bulk-download', methods=['GET'])
@api_login_required
def bulk_download_documents():
    try:
        ids_raw = request.args.get('ids', '')
        ids = [int(x) for x in ids_raw.split(',') if x.strip().isdigit()]
        
        service = get_service()
        return service.download_zip(ids)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@documents_bp.route('/generate-auto', methods=['POST'])
@api_login_required
def generate_document_auto():
    service = get_service()
    data = request.get_json() or {}
    doc = service.generate_from_template_auto(data) 
    return jsonify({"document": doc.to_dict()}), 201