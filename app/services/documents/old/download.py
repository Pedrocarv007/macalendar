import io
import zipfile
import os
from pathlib import Path
from datetime import datetime
from flask import send_file
from app.config.settings import Config

# Definimos quem pode baixar documentos de qualquer restaurante


def check_download_permission(document, user_role, user_restaurant_id):
    """Valida se o utilizador tem permissão para aceder ao documento."""
    if user_role in Config.STAFF_ROLES:
        return True
    if document.restaurant_id == user_restaurant_id:
        return True
    return False

def get_single_document(document, user_role, user_restaurant_id):
    """Prepara o envio de um único ficheiro."""
    if not check_download_permission(document, user_role, user_restaurant_id):
        raise PermissionError("Permissão negada para este documento")

    if not document.file_path or not Path(document.file_path).exists():
        raise FileNotFoundError("O ficheiro físico não existe no servidor")

    return send_file(
        document.file_path,
        as_attachment=True,
        download_name=document.filename or f"doc_{document.id}.png"
    )

def get_bulk_zip(documents, user_role, user_restaurant_id):
    """Gera um ZIP em memória com os documentos permitidos."""
    allowed_docs = [
        doc for doc in documents 
        if check_download_permission(doc, user_role, user_restaurant_id) 
        and doc.file_path and Path(doc.file_path).exists()
    ]

    if not allowed_docs:
        raise ValueError("Nenhum documento disponível ou válido para download")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for doc in allowed_docs:
            # arcname limpa o nome para o ZIP
            clean_name = f"{doc.document_type}_{doc.id}_{doc.filename}".replace(" ", "_")
            zf.write(doc.file_path, arcname=clean_name)

    zip_buffer.seek(0)
    zip_name = f"lote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=zip_name
    )