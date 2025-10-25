"""
Rotas de autenticação web (interface HTML)
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from app.models.user import User

auth_web_bp = Blueprint('auth_web', __name__)

@auth_web_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login web"""
    if request.method == 'POST':
        # Lógica de login será implementada aqui
        # Por enquanto redireciona para a API
        return redirect('/api/auth/login')
    
    return render_template('auth/login.html')

@auth_web_bp.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('auth_web.login'))