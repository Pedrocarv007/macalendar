"""
Rotas de autenticação web (interface HTML)
"""
from datetime import datetime
import traceback

from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from flask_jwt_extended import create_access_token

from app.extensions.database import db
from app.middleware.security import validate_email
from app.models.employee import Employee

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
            
            # Buscar employee no banco de dados (agora funciona como user)
            employee = Employee.query.filter_by(email=email).first()
            
            # Verificar credenciais usando o método seguro do modelo
            if not employee or not employee.check_password(password):
                flash('Email ou senha incorretos', 'danger')
                return render_template('auth/login.html')
            
            # Verificar se employee/usuário está ativo
            if not employee.is_active:
                flash('Conta inativa. Entre em contato com o administrador', 'warning')
                return render_template('auth/login.html')
            
            # Detectar primeiro login (antes de atualizar last_login)
            first_login = employee.last_login is None
            # Atualizar último login
            employee.last_login = datetime.utcnow()
            db.session.commit()
            
            # Criar token JWT para sessão
            additional_claims = {
                'role': employee.role,
                'restaurant_id': employee.restaurant_id,
                'department': employee.department,
                'name': employee.name
            }
            
            access_token = create_access_token(
                identity=str(employee.id),
                additional_claims=additional_claims
            )
            
            # Armazenar token e dados do usuário na sessão
            session['access_token'] = access_token
            session['user_id'] = employee.id
            session['user_name'] = employee.name
            session['user_role'] = employee.role
            session['user_email'] = employee.email
            session['restaurant_id'] = employee.restaurant_id
            
            # Configurar sessão permanente se "lembrar-me" estiver marcado
            if remember:
                session.permanent = True
                # A duração é definida em config (padrão 31 dias)
            else:
                session.permanent = False
            
            # Forçar troca de senha no primeiro login
            if first_login:
                session['must_change_pw'] = True
                flash('Primeiro acesso: por favor, altere sua senha.', 'warning')
            else:
                session.pop('must_change_pw', None)
            
            flash(f'Bem-vindo(a), {employee.name}!', 'success')
            
            # Redirecionar para a página solicitada ou dashboard
            next_page = request.args.get('next')
            if session.get('must_change_pw'):
                return redirect(url_for('web.profile'))
            if next_page:
                return redirect(next_page)
            return redirect(url_for('web.dashboard'))
            
        except Exception as e:
            print(f"[LOGIN ERROR] {str(e)}")
            traceback.print_exc()
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