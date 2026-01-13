#!/usr/bin/env python3
"""
Ponto de entrada da aplicação MAC Calendar
"""
import os
import sys
from io import StringIO
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask

# Configuração de caminhos
BASE_DIR = Path(__file__).resolve().parent

def load_env_file(env_path: Path) -> None:
    """Carrega .env suportando múltiplas codificações de arquivo."""
    if not env_path.exists():
        return

    encodings = ('utf-8', 'utf-8-sig', 'utf-16')
    for encoding in encodings:
        try:
            content = env_path.read_text(encoding=encoding)
            load_dotenv(stream=StringIO(content))
            return
        except (UnicodeDecodeError, Exception):
            continue
    
    # Fallback padrão se os específicos falharem
    load_dotenv(env_path)

# 1. Carregar ambiente ANTES de qualquer import do app
load_env_file(BASE_DIR / '.env')

# Imports do App (devem vir após o load_env_file)
from app import create_app
from app.config.iis_settings import IISConfig
from app.extensions.database import db

def resolve_config_name() -> str:
    """Determina o nome da configuração (CLI > ENV > Default)."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    return os.getenv('APP_CONFIG', 'default')

def setup_database(app: Flask):
    """Garante que as tabelas existam sem poluir o escopo global."""
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"Erro ao criar tabelas: {e}")

def main():
    config_name = resolve_config_name()
    app = create_app(config_name)

    # Configuração para IIS
    if os.getenv('RUNNING_ON_IIS') == 'True':
        app.config.from_object(IISConfig)

    if __name__ == '__main__':
        # 2. Inicialização do Banco de Dados
        setup_database(app)

        # 3. Configurações de execução com fallbacks seguros
        host = os.getenv('HOST')
        port = int(os.getenv('PORT'))
        debug = app.config.get('DEBUG')

        app.run(debug=debug, host=host, port=port)

if __name__ == '__main__':
    main()