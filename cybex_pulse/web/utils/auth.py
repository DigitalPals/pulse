"""
Authentication utilities for the web interface.
"""
from functools import wraps


def login_required(flask_redirect, flask_url_for, flask_session, is_authenticated_func):
    """Create a login_required decorator that redirects to the login page if not authenticated.
    
    Args:
        flask_redirect: The Flask redirect function
        flask_url_for: The Flask url_for function
        flask_session: The Flask session object
        is_authenticated_func: Function to check if the user is authenticated
        
    Returns:
        function: Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_authenticated_func():
                return flask_redirect(flask_url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def configuration_required(flask_redirect, flask_url_for, config):
    """Create a configuration_required decorator that redirects to setup wizard if app not configured.
    
    Args:
        flask_redirect: The Flask redirect function
        flask_url_for: The Flask url_for function
        config: Application configuration object
        
    Returns:
        function: Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not config.is_configured():
                return flask_redirect(flask_url_for('setup_wizard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator