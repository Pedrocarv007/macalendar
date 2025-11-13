"""
Rotas de autenticação web (interface HTML)
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from flask_jwt_extended import create_access_token
from datetime import datetime
from app.models.user import User
from app.middleware.security import validate_email
from app.extensions.database import db

auth_web_bp = Blueprint('auth_web', __name__)

@auth_web_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login web"""
    # Se já está logado, redireciona para dashboard
    if 'user_id' in session:
        return redirect(url_for('web.dashboard'))
    
    if request.method == 'POST':
        try:
            # Obter dados do formulário
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            remember = request.form.get('remember') == 'yes'
            
            # Validar campos obrigatórios
            if not email or not password:
                flash('Email e senha são obrigatórios', 'danger')
                return render_template('auth/login.html')
            
            # Validar formato de email
            if not validate_email(email):
                flash('Formato de email inválido', 'danger')
                return render_template('auth/login.html')
            
            # Buscar usuário no banco de dados
            user = User.query.filter_by(email=email).first()
            
            # Verificar credenciais usando o método seguro do modelo
            if not user or not user.check_password(password):
                flash('Email ou senha incorretos', 'danger')
                return render_template('auth/login.html')
            
            # Verificar se usuário está ativo
            if not user.is_active:
                flash('Conta inativa. Entre em contato com o administrador', 'warning')
                return render_template('auth/login.html')
            
            # Atualizar último login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Criar token JWT para sessão
            additional_claims = {
                'role': user.role,
                'restaurant_id': user.restaurant_id,
                'department': user.department,
                'name': user.name
            }
            
            access_token = create_access_token(
                identity=str(user.id),
                additional_claims=additional_claims
            )
            
            # Armazenar token e dados do usuário na sessão
            session['access_token'] = access_token
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_role'] = user.role
            session['user_email'] = user.email
            session['restaurant_id'] = user.restaurant_id
            
            # Configurar sessão permanente se "lembrar-me" estiver marcado
            if remember:
                session.permanent = True
                # A duração é definida em config (padrão 31 dias)
            else:
                session.permanent = False
            
            flash(f'Bem-vindo(a), {user.name}!', 'success')
            
            # Redirecionar para a página solicitada ou dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('web.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash('Erro ao processar login. Tente novamente.', 'danger')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@auth_web_bp.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('auth_web.login'))