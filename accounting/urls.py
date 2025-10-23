# accounting/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='app_root'),
    # 1. Основной рабочий URL (Панель управления)
    # Если в главном urls.py есть path('api/v1/', include('accounting.urls')),
    # этот путь будет доступен по /api/v1/dashboard/
    path('dashboard/', views.dashboard, name='dashboard'),

    # 2. Отчетность
    path('reports/', views.reports, name='reports'),

    # 3. Маршрут-заглушка для корня (для чистой обработки)
    # Добавьте этот путь, ТОЛЬКО если вам нужно, чтобы /api/v1/ попадал на дашборд.
    # Если вы используете path('', views.dashboard, name='app_root') в главном urls.py,
    # то он здесь не нужен.
    # path('', views.dashboard, name='app_root'),

    # 4. URL для пополнения баланса клиента (Оставьте, если это отдельный View)
    path(
        'deposit/<int:client_id>/<str:amount>/',
        views.deposit_funds,
        name='deposit_funds'
    ),

    # 5. URL для проведения и оплаты сеанса (Оставьте, если это отдельный View)
    path(
        'pay_session/<int:client_id>/<int:worker_id>/<str:session_cost>/',
        views.process_session_payment,
        name='process_session_payment'
    ),
]