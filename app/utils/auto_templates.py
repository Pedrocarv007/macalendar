from app.extensions.database import db
from app.models.document import Document
from app.models.calendar_event import CalendarEvent
import os
from datetime import datetime
from app.services.documents.templates import get_strategies

SYSTEM_USER_ID = 999 

def process_auto_generation(strategy_key, target, restaurant, photo_path, data, generator):
    # Recupera a data passada ou usa hoje como fallback
    data_real = data.get('data_evento', datetime.utcnow())

    strategies = get_strategies(target, restaurant, photo_path, data, generator)
    strat = strategies.get(strategy_key)

    if not strat:
        print(f"Erro: Estratégia '{strategy_key}' não reconhecida.")
        return None

    try:
        # 1. Executa a geração
        result = strat['method'](**strat['params'])

        # --- TRATAMENTO DE TUPLA (O SEGREDO ESTÁ AQUI) ---
        # Se o gerador devolve (imagem, caminho), pegamos apenas a imagem
        if isinstance(result, tuple):
            result = result[0] 
            print(f"ℹ️ Tupla detectada, extraindo primeiro elemento: {type(result)}")
        # -------------------------------------------------

        # 3. Define o nome e caminho do arquivo
     

        # --- LÓGICA DE SALVAMENTO ---
        elif isinstance(result, str):
            print(f"ℹ️ O gerador já devolveu um caminho: {result}")
        else:
            raise ValueError(f"O gerador retornou um tipo inesperado: {type(result)}")
        # 4. Cria o registro no Banco de Dados
        # Salva o caminho relativo para acesso web
        
        new_doc = Document(
            title=f"{strat['category']} - {target.name}",
            template_name="Auto Generated",
            file_path=result, # Caminho relativo para preview
            document_type=strat['category'],
            restaurant_id=target.restaurant_id,
            employee_id=SYSTEM_USER_ID,
            created_at=datetime.utcnow(),
            created_by=SYSTEM_USER_ID,
        )

       # 4. Cria o evento no calendário 
        new_event = CalendarEvent(
            title=f"Aniversário: {target.name}", 
            start_date=data_real, 
            end_date=data_real,
            event_type='event',
            location = result,
            description="""
                                        Parabéns pelo seu aniversário! Desejo muita saúde, sucesso e realizações, 
                                        tanto na vida pessoal quanto na profissional.
                                        Que você tenha um dia excelente e um ano de grandes conquistas. Felicidades!""", 
            restaurant_id=target.restaurant_id,
            created_by=SYSTEM_USER_ID
        )

        db.session.add(new_doc)
        db.session.add(new_event)
        db.session.commit()
        
        print(f"✅ LOG [SYSTEM]: {strat['category']} processado para {target.name}")
        return new_doc

    except Exception as e:
        db.session.rollback()
        print(f"❌ ERRO [SYSTEM]: Falha em {target.name}: {e}")
        return None