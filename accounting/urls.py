# accounting/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    # URL для пополнения баланса клиента
    # Заменяем <decimal:amount> на <str:amount>
    path(
        'deposit/<int:client_id>/<str:amount>/',
        views.deposit_funds,
        name='deposit_funds'
    ),
    # НОВЫЙ URL ДЛЯ ОТЧЕТНОСТИ
    path('reports/', views.reports, name='reports'),
    # URL для проведения и оплаты сеанса
    # Заменяем <decimal:session_cost> на <str:session_cost>
    path(
        'pay_session/<int:client_id>/<int:worker_id>/<str:session_cost>/',
        views.process_session_payment,
        name='process_session_payment'
    ),
]