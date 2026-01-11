"""
Rotas de autenticação web (interface HTML)
"""
from datetime import datetime
import traceback
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from flask_jwt_extended import create_access_token
from app.extensions.database import db, csrf
from app.middleware.security import validate_email
from app.models import employee
from app.utils.notifications import notify_login
from app.models.employee import Employee
from flask_jwt_extended import decode_token

auth_web_bp = Blueprint('auth_web', __name__)

@auth_web_bp.route('/login', methods=['GET', 'POST'])
@csrf.exempt
def login():
    """Página de login web"""

    return redirect("http://192.168.0.2:5005")
    
   

@auth_web_bp.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('auth_web.login'))




@auth_web_bp.route('/callback', methods=['POST', 'GET'])
def sso_callback():
    token = request.args.get('token')

    if not token:
        return "Token não fornecido", 400
 
    try:
        data = decode_token(token)
        user_email = data['sub']
        user = Employee.query.filter_by(email=user_email).first()
        if user:
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_role'] = user.role
            session['user_email'] = user.email
            session['restaurant_id'] = user.restaurant_id
            try:
                notify_login(user)
            except Exception:
                pass
            print(f"Usuário {user.id} logado via SSO.")
            return redirect(url_for('web.dashboard'))  # ou para a página principal do sistema
        else:
            return "Usuário não encontrado", 404
    except Exception as e:
        return f"Token inválido: {e}", 401