import os
import io
import zipfile
from pathlib import Path
from datetime import datetime
from flask import current_app, send_file
from werkzeug.utils import secure_filename
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
            query = query.filter(Document.document_type.ilike(category))

        # 3. Lógica de Hierarquia para Administradores
        current_restaurant_filter = self.restaurant_id
        if self.role in Config.SUPER_ROLES:
            req_restaurant_id = filters.get('restaurant_id')
            if req_restaurant_id and req_restaurant_id != 'todos':
                current_restaurant_filter = int(req_restaurant_id)
                query = query.filter(Document.restaurant_id == current_restaurant_filter)
            else:
                current_restaurant_filter = None # Sem filtro de restaurante (Ver tudo)
        else:
             query = query.filter(Document.restaurant_id == self.restaurant_id)


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
        if current_restaurant_filter:
             total_bytes = db.session.query(func.sum(Document.file_size)).filter(Document.restaurant_id == current_restaurant_filter).scalar() or 0
        else:
             total_bytes = db.session.query(func.sum(Document.file_size)).scalar() or 0

        
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
        is_worker_instance = isinstance(target, Worker)
        folder = 'workers' if is_worker_instance else 'employees'
        
        # Correção: Worker muitas vezes não tem photo_filename preenchido ou usa lógica diferente
        photo_filename = getattr(target, 'photo_filename', None)
        photo_path = str(self.base_upload_path / folder / photo_filename) if photo_filename else None

        strategies = get_strategies(target, restaurant, photo_path, extra_data, generator)
        config = strategies.get(document_type.lower())
        
        if not config: raise ValueError('Tipo de documento inválido')
        
        # Agora retorna (caminho_relativo, nome_arquivo)
        relative_path, filename = config['method'](**config['params'])
        
        # Se relative_path vier com barras invertidas (Windows), normalizar para web
        relative_path = relative_path.replace('\\', '/')

        # Resolver caminho absoluto para cálculo de tamanho (Assumindo estrutura root/uploads)
        # current_app.root_path aponta para /app, então .parent vai para raiz do projeto
        full_path = Path(current_app.root_path).parent / relative_path
        
        file_size = os.path.getsize(full_path) if full_path.exists() else 0

        doc = Document(
            title=f'Cartão - {target.name}',
            document_type="Foto",
            template_name=document_type,
            filename=filename,
            file_path=relative_path, # Salvando caminho relativo web-friendly
            file_size=file_size,
            file_extension="png",
            restaurant_id=restaurant.id,
            employee_id=None if is_worker_instance else target.id,
            worker_id=target.id if is_worker_instance else None,
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
        
        # Resolver caminho absoluto se estiver salvo como relativo
        file_path = doc.file_path
        if not os.path.isabs(file_path):
             # Tenta resolver primeiro em root/uploads (novo padrão)
             potential_path = Path(current_app.root_path).parent / file_path
             if potential_path.exists():
                 file_path = str(potential_path)
             else:
                 # Fallback para app/static (legado)
                 file_path = os.path.join(current_app.root_path, 'static', file_path)
             
        return send_file(file_path, as_attachment=True, download_name=doc.filename)

    def view_file(self, document_id):
        """Visualizar arquivo no navegador (inline)"""
        doc = Document.query.get_or_404(document_id)
        if not self._can_manage(doc):
            raise PermissionError("Acesso negado")

        # Resolver caminho absoluto se estiver salvo como relativo
        file_path = doc.file_path
        if not os.path.isabs(file_path):
             # Tenta resolver primeiro em root/uploads (novo padrão)
             potential_path = Path(current_app.root_path).parent / file_path
             if potential_path.exists():
                 file_path = str(potential_path)
             else:
                 # Fallback para app/static (legado)
                 file_path = os.path.join(current_app.root_path, 'static', file_path)
             
        return send_file(file_path, as_attachment=False)

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
    
    def upload(self, file, form_data):
        """Upload de um novo documento"""
        if not file:
             raise ValueError("Nenhum ficheiro fornecido")
             
        filename = secure_filename(file.filename)
        if not filename:
             raise ValueError("Nome de ficheiro inválido")

        # 1. Definir caminho de salvamento
        # Usa 'documents' dentro da pasta de uploads configurada
        save_dir = self.base_upload_path / 'documents'
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Gerar nome único para evitar sobrescrita
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        full_path = save_dir / unique_filename
        
        # 3. Salvar arquivo
        file.save(str(full_path))
        
        # 4. Calcular tamanho
        file_size = os.path.getsize(full_path)
        
        # 5. Calcular caminho relativo para o banco 
        # (Deve ser relativo ao root path ou uma convention consistente)
        # O sistema usa relative paths em muitos lugares. 
        # Se base_upload_path for '.../uploads', path relativo será 'documents/filename' ??
        # Na visualização (view_file), ele tenta resolver via upload folder.
        # Vamos salvar "documents/filename" se base_upload_path ja aponta para uploads.
        
        # Mas espere: self.base_upload_path = Path(current_app.config.get('UPLOAD_FOLDER'))
        # Se UPLOAD_FOLDER é absoluto...
        # Vamos salvar o caminho relativo à pasta 'uploads' se possível, ou 'uploads/documents/...' para ser seguro.
        
        # Olhando o `generate_from_template`, ele salva `file_path=relative_path`.
        # E relative_path é algo como 'uploads/generated/...'? 
        # (Não, relative_path lá é retornado pelo strategies)
        
        # Vamos assumir que guardar 'uploads/documents/xxx' é o padrão seguro visto nos exemplos do script de check
        # ID: 278, Path: uploads/generated/cartao_aniversario...
        
        relative_path = f"uploads/documents/{unique_filename}"
        
        # 6. Criar Registro
        doc = Document(
            title=form_data.get('title', filename),
            description=form_data.get('description'),
            document_type=form_data.get('document_type', 'Outros'),
            template_name='upload', 
            filename=unique_filename,
            file_path=relative_path,
            file_size=file_size,
            file_extension=filename.split('.')[-1].lower(),
            restaurant_id=self.restaurant_id, 
            created_by=self.user_id,
            status='uploaded',
            is_public=form_data.get('is_public') == 'true'
        )
        
        # Admin pode forçar outro restaurante
        if self.role in Config.SUPER_ROLES and form_data.get('restaurant_id'):
             try:
                 doc.restaurant_id = int(form_data.get('restaurant_id'))
             except:
                 pass

        db.session.add(doc)
        db.session.commit()
        
        self.log_activity('document_upload', f"Carregou documento: {doc.title}", doc.id, 'document')
        
        return doc