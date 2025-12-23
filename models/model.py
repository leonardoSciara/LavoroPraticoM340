from models.connection import db
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from functools import wraps
from flask import abort, redirect, url_for, flash


user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'))
)


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

    def __repr__(self):
        return f'<Role {self.name}>'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    roles = db.relationship('Role', 
                            secondary=user_roles, 
                            backref=db.backref('users', lazy='dynamic')
                            )
    ct_requests = db.relationship('CTRequest', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)

    def __str__(self):
        return f'User {self.username}'


class CTRequest(db.Model):
    __tablename__ = 'ct_request'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    machine_type = db.Column(db.String(50), nullable=False)
    machine_name = db.Column(db.String(50), nullable=False)
    machine_cpu = db.Column(db.Integer, nullable=False)
    machine_ram = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    ct_ip = db.Column(db.String(50))
    ct_hostname = db.Column(db.String(100))
    ct_user = db.Column(db.String(50))
    ct_password = db.Column(db.String(100))
    ct_vmid = db.Column(db.Integer)

    def __str__(self):
        return f'CTRequest {self.id} - {self.machine_name} - {self.status}'


def init_db():
    if not db.session.execute(db.select(Role).filter_by(name='admin')).scalars().first():
        admin_role = Role(name='admin')
        db.session.add(admin_role)
        db.session.commit()

    if not db.session.execute(db.select(Role).filter_by(name='user')).scalars().first():
        user_role = Role(name='user')
        db.session.add(user_role)
        db.session.commit()

    admin_user = db.session.execute(db.select(User).filter_by(username='administrator')).scalars().first()
    if not admin_user:
        admin_user = User(username="administrator")
        admin_user.set_password("Admin123!")
        admin_role = db.session.execute(db.select(Role).filter_by(name='admin')).scalars().first()
        if admin_role:
            admin_user.roles.append(admin_role)
        db.session.add(admin_user)
        db.session.commit()
    else:
        admin_role = db.session.execute(db.select(Role).filter_by(name='admin')).scalars().first()
        if admin_role and not admin_user.has_role('admin'):
            admin_user.roles.append(admin_role)
            db.session.commit()





def user_has_role(*role_names):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Devi essere autenticato per accedere a questa pagina.")
                return redirect(url_for('auth.login'))
            if not any(current_user.has_role(role) for role in role_names):
                flash("Non hai il permesso per accedere a questa pagina.")
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator