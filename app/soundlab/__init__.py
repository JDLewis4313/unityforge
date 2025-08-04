from flask import Blueprint

bp = Blueprint('soundlab', __name__)

from app.soundlab import routes