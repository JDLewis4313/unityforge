import sys
#print(f"REGISTERING LOGOS - Module: {__name__}, Import count: {len([m for m in sys.modules.keys() if 'logos' in m])}")

from flask import Blueprint

# Create blueprint with unique name to avoid conflicts
bp = Blueprint("logos", __name__)

# Import routes AFTER creating bp to avoid circular imports
from app.logos import routes

#print(f"LOGOS BLUEPRINT CREATED: {bp.name}")