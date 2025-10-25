"""
Configurações de banco de dados
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Instâncias das extensões
db = SQLAlchemy()
migrate = Migrate()

def init_database_extensions(app):
    """Inicializar extensões de banco de dados"""
    db.init_app(app)
    migrate.init_app(app, db)
    
    return db, migrate