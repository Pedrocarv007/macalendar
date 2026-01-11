
import os
from flask import jsonify
from app.config.settings import Config
from app.models.activity_log import ActivityLog
from app.models.document import Document
from app.models.employee import Employee
from app.models.workers import Worker
from app.models.restaurant import Restaurant
from pathlib import Path
from app.utils.document_generator import DocumentGenerator
from app.extensions.database import db
from app.services.documents.templates import get_strategies


base_path = Path("I:/testing/macalendar/app/static/uploads")


def validate_document_params(data, user_role, user_restaurant_id):
    document_type = data.get('document_type')
    is_worker = data.get('is_worker', False) # Padrão False se não vier
    employee_id = data.get('employee_id')
    restaurant_id = data.get('restaurant_id')

    if not all([employee_id, restaurant_id, document_type]):
        raise ValueError('Campos obrigatórios ausentes: employee_id, restaurant_id ou document_type')

    # Verificar restaurante
    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant:
        raise ValueError('Restaurante não encontrado')

    # Validação de permissão
    if user_role not in Config.VALID_ROLES and restaurant_id != user_restaurant_id:
        raise ValueError('Permissão negada para este restaurante')

    # Buscar Alvo (Worker ou Employee)
    Model = Worker if is_worker else Employee
    target = Model.query.get(employee_id) # .get() é mais direto que filter_by

    if not target:
        raise ValueError('Funcionário não encontrado')

    if not target.is_active:
        raise ValueError('O funcionário deve estar ativo para gerar documentos')

    # RETORNE OS OBJETOS AQUI
    return employee_id, restaurant_id, document_type, target, restaurant


def generate_templates(current_user_id, user_role, user_restaurant_id, data):
    # Agora recebemos o objeto 'target' e 'restaurant' diretamente
    employee_id, restaurant_id, document_type, target, restaurant = validate_document_params(
        data, user_role, user_restaurant_id
    )
    
    # 2. Instanciar o Gerador que você postou
    generator = DocumentGenerator()

    # IMPORTANTE: Definir is_worker baseado no que veio no data
    is_worker = data.get('is_worker', False)
    folder = 'workers' if is_worker else 'employees'

    photo_path = None
    if target.photo_filename:
        photo_path = str(base_path / folder / target.photo_filename)

    strategies = get_strategies(target, restaurant, photo_path, data, generator)
    config = strategies.get(document_type.lower())
    
    if not config:
        raise ValueError('Tipo de documento inválido')

    # EXECUÇÃO DA SUA CLASSE PIL
    file_path, filename = config['method'](**config['params'])

    # 5. Salvar Registro no Banco (DRY)
    document = Document(
        title=f'Cartão - {target.name}',
        document_type="Foto",
        template_name=document_type,
        filename=filename,
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        file_extension = "png",
        restaurant_id=restaurant_id,
        employee_id=None if is_worker else target.id,
        worker_id=target.id if is_worker else None,
        created_by=current_user_id,
        status='generated'
    )
    
    db.session.add(document)
     # Registrar atividade
    ActivityLog.log_activity(
            activity_type='document_generated',
            description=f'Documento gerado automaticamente ({config["category"]}) para {target.name}',
            user_id=current_user_id,
            restaurant_id=restaurant_id,
            target_id=document.id,
            target_type='document'
        )

    db.session.commit()
    
    return jsonify({'message': 'Sucesso!', 'document': document.to_dict()}), 201