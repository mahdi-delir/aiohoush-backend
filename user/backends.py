from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission


class PermissionOverrideBackend(ModelBackend):
    """Group/direct grants minus per-user denials; active superusers bypass.

    Configure this as the only AUTHENTICATION_BACKENDS entry. Like Django's
    permission caches, the denial cache lives on the User instance. Fetch a
    fresh User after changing permissions or memberships.
    """

    def _get_denied_permissions(self, user_obj):
        if not hasattr(user_obj, "_denied_perm_cache"):
            rows = user_obj.denied_permissions.values_list(
                "content_type__app_label", "codename"
            ).order_by()
            user_obj._denied_perm_cache = {
                f"{app_label}.{codename}" for app_label, codename in rows
            }
        return user_obj._denied_perm_cache

    async def _aget_denied_permissions(self, user_obj):
        if not hasattr(user_obj, "_denied_perm_cache"):
            rows = user_obj.denied_permissions.values_list(
                "content_type__app_label", "codename"
            ).order_by()
            user_obj._denied_perm_cache = {
                f"{app_label}.{codename}" async for app_label, codename in rows
            }
        return user_obj._denied_perm_cache

    def _filter_permissions(self, user_obj, permissions):
        if not permissions or user_obj.is_superuser:
            return permissions
        return permissions - self._get_denied_permissions(user_obj)

    async def _afilter_permissions(self, user_obj, permissions):
        if not permissions or user_obj.is_superuser:
            return permissions
        return permissions - await self._aget_denied_permissions(user_obj)

    def get_user_permissions(self, user_obj, obj=None):
        permissions = super().get_user_permissions(user_obj, obj=obj)
        return self._filter_permissions(user_obj, permissions)

    async def aget_user_permissions(self, user_obj, obj=None):
        permissions = await super().aget_user_permissions(user_obj, obj=obj)
        return await self._afilter_permissions(user_obj, permissions)

    def get_group_permissions(self, user_obj, obj=None):
        permissions = super().get_group_permissions(user_obj, obj=obj)
        return self._filter_permissions(user_obj, permissions)

    async def aget_group_permissions(self, user_obj, obj=None):
        permissions = await super().aget_group_permissions(user_obj, obj=obj)
        return await self._afilter_permissions(user_obj, permissions)

    def with_perm(self, perm, is_active=True, include_superusers=True, obj=None):
        users = super().with_perm(
            perm,
            is_active=is_active,
            include_superusers=include_superusers,
            obj=obj,
        )
        if obj is not None:
            return users

        if isinstance(perm, Permission):
            denied_filter = {"denied_permissions__pk": perm.pk}
        else:
            # The parent has already validated the permission argument.
            app_label, codename = perm.split(".")
            denied_filter = {
                "denied_permissions__content_type__app_label": app_label,
                "denied_permissions__codename": codename,
            }

        denied_users = (
            get_user_model()._default_manager.using(users.db)
            .filter(is_superuser=False, **denied_filter)
            .values("pk")
        )
        return users.exclude(pk__in=denied_users)
