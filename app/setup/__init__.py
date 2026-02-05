from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from app.database import db
from app.models import User
import os

setup_bp = Blueprint('setup', __name__, template_folder='../../templates/setup', url_prefix='/setup')

@setup_bp.route('/', methods=['GET'])
def index():
    # If users exist, setup is complete
    if User.query.first():
        return redirect(url_for('auth.login'))
    return render_template('index.html')

@setup_bp.route('/complete', methods=['GET'])
def complete():
    return render_template('complete.html')
