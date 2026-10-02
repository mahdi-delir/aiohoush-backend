from typing import Any

from user.models import User


def get_user_data(
    *,
    user: User,
) -> dict[str, Any]:
    return {}