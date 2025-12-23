from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager

from routes.default import app as bp_default
from routes.api import app as bp_api
from routes.auth import app as bp_auth
from routes.vm import app as bp_ct

from models.connection import db
from models.model import User
from models.model import *
import os

from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

app.register_blueprint(bp_default)
app.register_blueprint(bp_api, url_prefix='/api')
app.register_blueprint(bp_auth)
app.register_blueprint(bp_ct)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 165465)

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()

login_manager.login_view = 'auth.login'
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    stmt = db.select(User).filter_by(id=user_id)
    user = db.session.execute(stmt).scalar_one_or_none()
    return user


with app.app_context():
    db.create_all()
    init_db()


if __name__ == "__main__":
    app.run(debug=True)

 