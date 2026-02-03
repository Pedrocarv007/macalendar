import os
import io
import zipfile
from pathlib import Path
from datetime import datetime
from flask import current_app, send_file
from sqlalchemy import func, or_
from app.extensions.database import db
from app.models.document import Document
from app.models.employee import Employee
from app.models.workers import Worker
from app.models.restaurant import Restaurant
from app.utils.document_generator import DocumentGenerator
from app.services.documents.templates import get_strategies
from app.config.settings import Config
from app.services.base_service import BaseService


class DocumentService(BaseService):
    def __init__(self, user_id, user_role, user_restaurant_id):
        self.user_id = user_id
        self.role = user_role
        self.restaurant_id = user_restaurant_id
        self.base_upload_path = Path(current_app.config.get('UPLOAD_FOLDER'))

    # --- PRIVADOS (AUXILIARES) ---
    def _can_manage(self, document):
        if self.role in Config.SUPER_ROLES: return True
        return document.restaurant_id == self.restaurant_id

    # --- CRUD ---
    def list(self, filters):
        query = Document.query
        
        # 1. Busca textual
        search = filters.get('search')
        if search:
            term = f"%{search}%"
            query = query.filter(or_(Document.title.ilike(term), Document.description.ilike(term)))


        # 2. Categoria (Certificados, Manuais, etc)
        category = filters.get('document_type')
        if category and category != 'todos':
            query = query.filter(or_(Document.document_type.ilike(category), Document.document_type.ilike(category)))

        # 3. Lógica de Hierarquia para Administradores
        if self.role not in Config.SUPER_ROLES:
            # Usuário Comum: Sempre travado no restaurante dele
            query = query.filter(Document.restaurant_id == self.restaurant_id)
        else:
            # Admin: Verifica se ele escolheu um restaurante específico no select
            req_restaurant_id = filters.get('restaurant_id')
            if req_restaurant_id and req_restaurant_id != 'todos':
                query = query.filter(Document.restaurant_id == int(req_restaurant_id))



        sort_by = filters.get('sortBy', 'upload_date')
        if sort_by == 'name':
            query = query.order_by(Document.title.asc())
        elif sort_by == 'size':
            query = query.order_by(Document.file_size.desc())
        else: # Default: upload_date
            query = query.order_by(Document.created_at.desc())

        # Paginação
        page = int(filters.get('page', 1))
        pagination = query.paginate(page=page, per_page=8)

            # Contagens para o Dashboard
        total_geral = query.count()
        pdf_count = query.filter(Document.filename.ilike('%.pdf%')).count()
        # Aqui usamos 'Fotos' se for assim que está no seu banco:
        image_count = query.filter(Document.document_type == 'Foto').count() 
        
        # Soma do tamanho de todos os arquivos filtrados
        total_bytes = db.session.query(func.sum(Document.file_size)).filter(Document.restaurant_id == self.restaurant_id).scalar() or 0

        
        return {
                'items': [d.to_dict() for d in pagination.items],
                'total': total_geral,
                'pdf': pdf_count,
                'image': image_count, 
                'total_size_bytes': total_bytes,
                'pages': pagination.pages,
                'current_page': page
            }
    def update(self, document_id, data):
        document = Document.query.get.get_or_404(document_id)

        if not self._can_manage(document):
            raise PermissionError("Não tens Permissão para editar este documento.")
        
        for field in ['title', 'description', 'tags', 'status', 'is_public' ]:
            if field in data:
                setattr(document, field, data[field])
        

        document.updated_at = datetime.utcnow()
        db.session.commit()

        self.log_activity('document_updated', f"Editou {document.title}", document.id, 'document')
        return document
    
    def delete(self, document_id):
        document = Document.query.get_or_404(document_id)

        if not self._can_manage(document):
            raise PermissionError("Não tens permissão para deletar esse documento")
        
        if document.file_path:
            try:
                path = Path(document.file_path)
                if path.exists():
                    path.unlink()
            except Exception as e:
                raise ValueError(f"Erro ao apagar ficheiro {e}")
            
        title_for_log = document.title

        db.session.delete(document)
        db.session.commit()

        self.log_activity('Documento deletado', f"Eliminou: {title_for_log}")
        return True
    
    def get_stats(self):
        query = Document.query
        if self.role not in Config.SUPER_ROLES:
            query = query.filter(Document.restaurant_id == self.restaurant_id)
            
        return {
            'total': query.count(),
            'pdf': query.filter(Document.file_extension.ilike('pdf')).count(),
            'images': query.filter(Document.file_extension.in_(['jpg', 'jpeg', 'png', 'webp'])).count()
        }

    # --- GERAÇÃO DE TEMPLATES 

    def generate_from_template_auto(self, data):
            """Este é o método que a ROTA chama. Ele resolve os IDs em Objetos."""
            employee_id = data.get('employee_id')
            restaurant_id = data.get('restaurant_id')
            document_type = data.get('document_type')
            is_worker = data.get('is_worker', False)

            if not all([employee_id, restaurant_id, document_type]):
                raise ValueError('Campos obrigatórios ausentes: employee_id, restaurant_id ou document_type')

            # 1. Buscar Restaurante
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant: raise ValueError('Restaurante não encontrado')

            # 2. Validar Permissão
            if self.role not in Config.SUPER_ROLES and restaurant_id != self.restaurant_id:
                raise PermissionError('Permissão negada para este restaurante')

            # 3. Buscar Alvo (Worker ou Employee)
            Model = Worker if is_worker else Employee
            target = Model.query.get(employee_id)
            if not target: raise ValueError('Funcionário não encontrado')

            # 4. Chamar a geração propriamente dita
            return self.generate_from_template(target, restaurant, document_type, data)

    def generate_from_template(self, target, restaurant, document_type, extra_data):
        generator = DocumentGenerator()
        
        # Lógica de caminho de foto integrada
        folder = 'workers' if hasattr(target, 'worker_id') else 'employees'
        photo_path = str(self.base_upload_path / folder / target.photo_filename) if target.photo_filename else None

        strategies = get_strategies(target, restaurant, photo_path, extra_data, generator)
        config = strategies.get(document_type.lower())
        
        if not config: raise ValueError('Tipo de documento inválido')

        file_path, filename = config['method'](**config['params'])

        doc = Document(
            title=f'Cartão - {target.name}',
            document_type="Foto",
            template_name=document_type,
            filename=filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            file_extension="png",
            restaurant_id=restaurant.id,
            employee_id=None if folder == 'workers' else target.id,
            worker_id=target.id if folder == 'workers' else None,
            created_by=self.user_id,
            status='generated'
        )

        db.session.add(doc)
        db.session.commit()
        self.log_activity('document generated', f"Gerado: {doc.title}", doc.id, 'Aviso')
        return doc

    # --- DOWNLOADS ---
    def download_single(self, document_id):
        doc = Document.query.get_or_404(document_id)
        if not self._can_manage(doc):
            raise PermissionError("Acesso negado")

        self.log_activity('download', f"Descarregou: {doc.title}", doc.id, 'document')   
        return send_file(doc.file_path, as_attachment=True, download_name=doc.filename)

    def download_zip(self, document_ids):
        docs = Document.query.filter(Document.id.in_(document_ids)).all()
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            for d in docs:
                if self._can_manage(d) and Path(d.file_path).exists():
                    zf.write(d.file_path, arcname=f"{d.id}_{d.filename}")

        zip_buffer.seek(0)
        return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, 
                         download_name=f"lote_{datetime.now().strftime('%Y%m%d')}.zip")
    
    def upload(self, data, form):
        pass