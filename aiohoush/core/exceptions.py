from rest_framework.views import exception_handler

from django.utils.translation import gettext_lazy as _

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    original_data = response.data
    message = _("درخواست نامعتبر است.")
    if (
        isinstance(original_data, dict)
        and isinstance(original_data.get("detail"), str)
    ):
        message = original_data["detail"]
    response.data = {
        "success": False,
        "message": message,
        "called_by": 'webapp',
        "detail": original_data,
    }
    return response
