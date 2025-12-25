"""
Inicialização das extensões Flask
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_wtf.csrf import CSRFProtect

# Instâncias globais das extensões
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
csrf = CSRFProtect()

def init_db(app):
    """Inicializar banco de dados"""
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    csrf.init_app(app)
    
    return db