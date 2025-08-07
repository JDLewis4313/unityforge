from app import db
from app.api import bp
from app.api.auth import basic_auth, token_auth


@bp.route('/tokens', methods=['POST'])
@basic_auth.login_required
def get_token():
    token = basic_auth.current_user().get_token()
    db.session.commit()
    return {'token': token}


@bp.route('/tokens', methods=['DELETE'])
@token_auth.login_required
def revoke_token():
    token_auth.current_user().revoke_token()
    db.session.commit()
    return '', 204


@bp.route('/csrf-token', methods=['GET'])
def get_csrf_token():
    """Get a fresh CSRF token"""
    from flask_wtf.csrf import generate_csrf
    return {'csrf_token': generate_csrf()}