"""
URL configuration for aiohoush project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('user.urls')),
    path("course/", include("course.urls")),
    path("order/", include("order.urls")),
    path("accounting/", include("accounting.urls")),
    path("ticket/", include("ticket.urls")),
    path("project/", include("project.urls")),
]

# سرو فایل‌های آپلودی در محیط توسعه (DEBUG). در production این مسیر
# باید توسط وب‌سرور یا سرویس فایل هاست سرو شود؛ static() وقتی DEBUG
# خاموش است یا MEDIA_URL آدرس کامل است، چیزی اضافه نمی‌کند.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
