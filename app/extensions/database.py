"""
Inicialização das extensões Flask
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

# Instâncias globais das extensões
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def init_db(app):
    """Inicializar banco de dados"""
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    
    return db