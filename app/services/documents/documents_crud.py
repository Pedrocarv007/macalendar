import os
from pathlib import Path
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app, session
from app.extensions.database import db
from app.models.document import Document
from app.models.employee import Employee
from app.models.activity_log import ActivityLog
from app.config.settings import Config
from sqlalchemy import or_

# --- AUXILIARES ---

def can_manage_document(document, user_role, user_restaurant_id):
    """Centraliza a lógica de permissão para leitura e escrita."""
    if user_role in Config.SUPER_ROLES:
        return True
    if user_role in Config.STAFF_ROLES and document.restaurant_id == user_restaurant_id:
        return True
    return document.restaurant_id == user_restaurant_id

# --- Funções trabalhadoras/escravas ---

def list_documents(user_role, user_restaurant_id, filters):
    """Filtra documentos com base no cargo, restaurante e termos de busca."""
    query = Document.query

    # 1. Filtro de Busca Global (O que torna o sistema fluido ao digitar)
    search_term = filters.get('search')
    if search_term:
        search_term = f"%{search_term}%"
        query = query.filter(or_(
            Document.file_extension.ilike(search_term),
            Document.description.ilike(search_term),
            Document.tags.ilike(search_term)
        ))

    # 2. Filtros Exatos
    if filters.get('document_type'):
        query = query.filter(Document.document_type.ilike(f"%{filters['document_type']}%"))

    if filters.get('employee_id'):
        query = query.filter(Document.employee_id == filters['employee_id'])
    
    if filters.get('worker_id'):
        query = query.filter(Document.worker_id == filters['worker_id'])

    # 3. Filtro de Hierarquia (Restaurante)
    if user_role not in Config.SUPER_ROLES and user_role not in Config.STAFF_ROLES:
        query = query.filter(Document.restaurant_id == user_restaurant_id)
    elif filters.get('restaurant_id'):
        query = query.filter(Document.restaurant_id == filters['restaurant_id'])

    # 4. Ordenação Dinâmica
    sort_by = filters.get('sortBy', 'date')
    if sort_by == 'name':
        query = query.order_by(Document.title.asc())
    elif sort_by == 'size':
        query = query.order_by(Document.file_size.desc())
    else:
        query = query.order_by(Document.created_at.desc())

    #Stats e paginação do sistema de documentos

    page = int(filters.get('page', 1))
    per_page = 8  # Número de documentos por página
    
    total_count = query.count()
    # .offset() pula os registros das páginas anteriores
    # .limit() pega apenas a quantidade da página atual
    documents = query.offset((page - 1) * per_page).limit(per_page).all()


    pdf_count = query.filter(Document.file_extension.ilike('pdf')).count()
    img_count = query.filter(or_(
        Document.filename.ilike('%.jpg'),
        Document.filename.ilike('%.jpeg'),
        Document.filename.ilike('%.png'),
        Document.filename.ilike('%.webp')
    )).count()

    stats = {
        'total': total_count,
        'pages': (total_count + per_page - 1) // per_page, # Cálculo do total de páginas
        'current_page': page,
        'pdf': pdf_count,
        'image': img_count
    }

    return documents, stats

def upload_document(file, form_data, current_user_id, user_role, user_restaurant_id):
    """Gere o upload físico e o registo no banco de dados."""
    restaurant_id =  session.get('restaurant_id')
    category = form_data.get('category')

    if not restaurant_id or not category:
        print(restaurant_id, category)
        raise ValueError('Restaurant ID e Categoria são obrigatórios')

    if user_role not in Config.SUPER_ROLES and restaurant_id != user_restaurant_id:
        raise PermissionError('Permissão negada para este restaurante')

    # Configuração de caminhos com Pathlib
    uploads_root = Path(current_app.config.get('UPLOAD_FOLDER'))
    upload_folder = uploads_root / 'documents' / str(restaurant_id)
    upload_folder.mkdir(parents=True, exist_ok=True)

    filename = secure_filename(f"{int(datetime.now().timestamp())}_{file.filename}")
    file_path = upload_folder / filename
    file.save(str(file_path))

    file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''

    document = Document(
        title=form_data.get('name') or file.filename,
        document_type=category,
        template_name=category,
        filename=filename,
        file_path=str(file_path),
        file_size=os.path.getsize(file_path),
        file_extension = file_ext,
        restaurant_id=restaurant_id,
        employee_id=form_data.get('employee_id', type=int) or current_user_id,
        created_by=current_user_id,
        description=form_data.get('description'),
        tags=form_data.get('tags'),
        is_public=form_data.get('is_public') == 'true',
        status='uploaded'
    )

    db.session.add(document)
    ActivityLog.log_activity(
        activity_type='document_uploaded',
        description=f"Documento enviado: {document.title}",
        user_id=current_user_id,
        restaurant_id=restaurant_id,
        target_id=document.id,
        target_type='document'
    )
    db.session.commit()
    return document

def update_document(document, data, user_role, user_restaurant_id):
    """Atualiza campos permitidos."""
    if not can_manage_document(document, user_role, user_restaurant_id):
        raise PermissionError("Permissão negada para atualizar este documento")

    for field in ['title', 'content', 'template_name', 'status']:
        if field in data:
            setattr(document, field, data[field])

    document.updated_at = datetime.utcnow()
    db.session.commit()
    return document

def delete_document(document, user_role, user_restaurant_id):
    """Remove o ficheiro e o registo."""
    if not can_manage_document(document, user_role, user_restaurant_id):
        raise PermissionError("Permissão negada para eliminar este documento")

    if document.file_path and Path(document.file_path).exists():
        try:
            os.remove(document.file_path)
        except OSError:
            pass

    db.session.delete(document)
    db.session.commit()