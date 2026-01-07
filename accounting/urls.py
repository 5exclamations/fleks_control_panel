from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='app_root'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('reports/', views.reports, name='reports'),

    path('transactions/<int:transaction_id>/print-receipt/', views.print_receipt, name='print_receipt'),
    path('transactions/<int:transaction_id>/view-receipt/', views.view_receipt, name='view_receipt'),
    path('transactions/<int:transaction_id>/view-receipt/pdf/', views.view_receipt, {'format': 'pdf'}, name='view_receipt_pdf'),
    path('transactions/<int:transaction_id>/download-receipt/', views.download_receipt_pdf, name='download_receipt_pdf'),

]