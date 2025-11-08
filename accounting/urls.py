from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='app_root'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('reports/', views.reports, name='reports'),

    path('transactions/<int:transaction_id>/print-receipt/', views.print_receipt, name='print_receipt'),


]