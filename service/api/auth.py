"""Authentication middleware for the API."""

from aws_lambda_powertools.middleware_factory import lambda_handler_decorator
from aws_lambda_powertools.utilities.typing import LambdaContext

from service.shared.config import get_auth_settings


@lambda_handler_decorator
def require_auth(handler, event: dict, context: LambdaContext):
    """Middleware to validate Bearer token in Authorization header.

    Returns 401 Unauthorized if:
    - Authorization header is missing
    - Token format is invalid (not "Bearer <token>")
    - Token is not in the list of valid tokens
    """
    auth_settings = get_auth_settings()
    valid_tokens = auth_settings.bearer_tokens

    # If no tokens configured, allow all requests (for development/testing)
    if not valid_tokens:
        return handler(event, context)

    # Get Authorization header (case-insensitive)
    headers = event.get('headers', {}) or {}
    auth_header = None
    for key, value in headers.items():
        if key.lower() == 'authorization':
            auth_header = value
            break

    if not auth_header:
        return {
            'statusCode': 401,
            'body': '{"message": "Missing Authorization header"}',
            'headers': {'Content-Type': 'application/json'},
        }

    # Validate Bearer token format
    if not auth_header.startswith('Bearer '):
        return {
            'statusCode': 401,
            'body': '{"message": "Invalid Authorization header format. Use: Bearer <token>"}',
            'headers': {'Content-Type': 'application/json'},
        }

    token = auth_header[7:]  # Remove "Bearer " prefix

    if token not in valid_tokens:
        return {
            'statusCode': 401,
            'body': '{"message": "Invalid token"}',
            'headers': {'Content-Type': 'application/json'},
        }

    # Token is valid, proceed to handler
    return handler(event, context)
