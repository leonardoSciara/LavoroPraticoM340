from flask import request, redirect, url_for, flash
from flask import Blueprint
from flask import render_template

from models.model import User, Role
from models.connection import db

from flask_login import current_user

from flask_login import login_required

from flask_login import login_user
from flask_login import logout_user
from models.model import user_has_role




app = Blueprint('auth', __name__)


@app.route('/login')
def login():
    return render_template('auth/login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    if not username or not password:
        flash('Inserisci username e password')
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(username=username).first()

    if not user:
        flash(f'Utente "{username}" non trovato')
        return redirect(url_for('auth.login'))
    if not user.check_password(password):
        flash('Password errata')
        return redirect(url_for('auth.login'))

    login_user(user, remember=remember)
    flash(f'Benvenuto {user.username}!')
    return redirect(url_for('ct.ct_dashboard'))  




@app.route('/signup')
def signup():
    return render_template('auth/signup.html')

@app.route('/signup', methods=['POST'])
def signup_post():
    username = request.form.get('username')
    password = request.form.get('password')
    password_confirm = request.form.get('password_confirm')
    
    if not username or not password:
        flash('Inserisci username e password')
        return redirect(url_for('auth.signup'))
    
    if password != password_confirm:
        flash('Le password non corrispondono')
        return redirect(url_for('auth.signup'))
    
    if len(password) < 6:
        flash('La password deve essere di almeno 6 caratteri')
        return redirect(url_for('auth.signup'))
    
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash(f'Username "{username}" già esistente')
        return redirect(url_for('auth.signup'))
    
    user_role = Role.query.filter_by(name='user').first()
    if not user_role:
        flash('Errore: ruolo user non trovato')
        return redirect(url_for('auth.signup'))
    
    new_user = User(username=username)
    new_user.set_password(password)
    new_user.roles.append(user_role)
    
    db.session.add(new_user)
    db.session.commit()
    
    flash('Registrazione completata! Ora puoi effettuare il login.')
    return redirect(url_for('auth.login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('eseguito logout')
    return redirect(url_for('auth.login'))