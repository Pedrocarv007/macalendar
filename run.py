#!/usr/bin/env python3
"""
Ponto de entrada da aplicação MAC Calendar
"""
import os
from app import create_app
from app.extensions.database import db

# Criar aplicação
app = create_app()

if __name__ == '__main__':
    # Configurações para desenvolvimento
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    
    # Criar tabelas se não existirem
    with app.app_context():
        db.create_all()
    
    # Executar aplicação
    app.run(
        debug=debug_mode,
        host=host,
        port=port
    )