from typing import Any

from rest_framework.response import Response


class APIResponse(Response):
    def __init__(
        self,
        *,
        success: bool,
        message: str,
        called_by: str,
        data: Any = None,
        detail: Any = None,
        status: int | None = None,
        headers: dict | None = None,
    ):
        payload = {
            "success": success,
            "message": message,
            "called_by": called_by,
        }

        if detail is not None:
            payload["detail"] = detail

        if data is not None:
            payload["data"] = data

        super().__init__(
            data=payload,
            status=status,
            headers=headers,
        )