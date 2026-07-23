"""
Core utility functions shared across apps.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler that returns consistent JSON error responses.
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            'success': False,
            'error': str(exc),
            'status_code': response.status_code,
        }
        if hasattr(response, 'data'):
            if isinstance(response.data, dict):
                error_data['details'] = response.data
            else:
                error_data['details'] = {'non_field_errors': response.data}
        response.data = error_data
    else:
        logger.exception("Unhandled exception in API view", exc_info=exc)
        response = Response(
            {
                'success': False,
                'error': 'Ocorreu um erro interno. Tente novamente.',
                'status_code': 500,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


def success_response(data=None, message='', status_code=200, **kwargs):
    """
    Builds a standardised success response dict.
    """
    payload = {'success': True}
    if message:
        payload['message'] = message
    if data is not None:
        payload['data'] = data
    payload.update(kwargs)
    return payload


def get_client_ip(request):
    """Extract real client IP from request headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def paginate_queryset(queryset, page=1, per_page=20):
    """
    Simple manual pagination helper.
    Returns (items, total, pages) tuple.
    """
    total = queryset.count()
    pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page
    items = queryset[offset:offset + per_page]
    return items, total, pages
