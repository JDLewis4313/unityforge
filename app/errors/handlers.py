from flask import render_template, request, current_app
from app import db
from app.errors import bp
from app.api.errors import error_response as api_error_response
from app.email import send_email

def wants_json_response():
    return request.accept_mimetypes['application/json'] >= \
        request.accept_mimetypes['text/html']

@bp.app_errorhandler(404)
def not_found_error(error):
    if wants_json_response():
        return api_error_response(404)
    return render_template('errors/404.html'), 404

@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    
    # Send email to admins about the error
    if current_app.config['ADMINS'] and not current_app.debug:
        send_error_notification(error)
    
    if wants_json_response():
        return api_error_response(500)
    return render_template('errors/500.html'), 500

@bp.app_errorhandler(413)
def too_large_error(error):
    return render_template('errors/413.html'), 413

def send_error_notification(error):
    """Send email to admins when 500 error occurs."""
    try:
        admins = current_app.config['ADMINS']
        if admins:
            error_text = f"""
            Error: {str(error)}
            Request URL: {request.url}
            Method: {request.method}
            IP: {request.remote_addr}
            User Agent: {request.user_agent}
            """
            
            send_email(
                '[UnityForge] Application Error',
                sender=current_app.config['MAIL_DEFAULT_SENDER'],
                recipients=admins,
                text_body=error_text,
                html_body=f'<pre>{error_text}</pre>',
                sync=True  # Send synchronously for error emails
            )
    except Exception as e:
        # Don't let email errors crash the app
        current_app.logger.error(f'Failed to send error email: {e}')