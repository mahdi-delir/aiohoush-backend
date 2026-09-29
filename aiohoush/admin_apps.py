from django.contrib.admin.apps import AdminConfig


class AiohoushAdminConfig(AdminConfig):
    default_site = "aiohoush.admin_site.AiohoushAdminSite"