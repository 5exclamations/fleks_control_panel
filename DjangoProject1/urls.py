"""
URL configuration for DjangoProject1 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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

from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    path('i18n/setlang/', include('django.conf.urls.i18n')),  # Переключение языка
]

urlpatterns += i18n_patterns(
    # Admin Panel
    path('admin/', admin.site.urls),

    path('api/v1/', include('accounting.urls')),

    # Root path
    path('', include('accounting.urls')),
    prefix_default_language=False,  # Не добавлять префикс для языка по умолчанию
)