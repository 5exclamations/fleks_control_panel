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
from django.urls import path, include  # Импортируем include

urlpatterns = [
    # 1. Административная панель
    path('admin/', admin.site.urls),

    # 2. Основные URL-адреса нашего приложения accounting
    path('api/v1/', include('accounting.urls')),

    # 3. КОРНЕВОЙ URL ('/') - Измените это
    # Направляем корень на Dashboard
    path('', include('accounting.urls')),
    # Внимание: убедитесь, что в accounting/urls.py НЕТ пустого пути.
]