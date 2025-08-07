from flask import Blueprint

bp = Blueprint('prayer', __name__, url_prefix='/prayer')

from app.prayer import routes