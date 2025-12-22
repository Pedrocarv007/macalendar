#!/usr/bin/env python3
"""
Ponto de entrada da aplicação MAC Calendar
"""
import os
import sys
from io import StringIO
from pathlib import Path

from dotenv import load_dotenv

# Carregar variáveis do arquivo .env na raiz do projeto
BASE_DIR = Path(__file__).resolve().parent


def load_env_file(env_path: Path) -> None:
    """Carrega .env suportando arquivos com BOM ou codificação UTF-16."""

    if not env_path.exists():
        load_dotenv(env_path)
        return

    encodings = ('utf-8', 'utf-8-sig', 'utf-16', 'utf-16le', 'utf-16be')

    for encoding in encodings:
        try:
            with env_path.open('r', encoding=encoding) as pointer:
                content = pointer.read()
        except UnicodeDecodeError:
            continue
        else:
            load_dotenv(stream=StringIO(content))
            return

    # Se nenhuma codificação funcionou, usar comportamento padrão
    load_dotenv(env_path)


load_env_file(BASE_DIR / '.env')

# Importar após carregar .env para que os.getenv() funcione em settings.py
from app import create_app
from app.config.iis_settings import IISConfig
from app.extensions.database import db


def resolve_config_name() -> str:
    """Determinar qual configuração utilizar."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    return os.getenv('APP_CONFIG') 


CONFIG_NAME = resolve_config_name()

# Criar aplicação com a configuração selecionada
app = create_app(CONFIG_NAME)



# Ajustes específicos quando executado atrás do IIS
if os.getenv('RUNNING_ON_IIS'):
    app.config.from_object(IISConfig)


if __name__ == '__main__':
    debug_mode = app.config.get('DEBUG')
    port = os.getenv('PORT')
    host = os.getenv('HOST')

    # Criar tabelas se não existirem
    with app.app_context():
        db.create_all()
    
    # Exibir configuração ativa
    print(f"Iniciando MAC Calendar com config '{CONFIG_NAME}' em {host}:{port} (debug={debug_mode})")

    # Executar aplicação
    app.run(debug=debug_mode, host=host, port=port)