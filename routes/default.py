from flask import Blueprint, redirect, url_for
from flask_login import current_user

app = Blueprint('default', __name__)

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('ct.ct_dashboard'))
    return redirect(url_for('auth.login'))