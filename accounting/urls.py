from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='app_root'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_user, name='logout_user'),

    path('reports/', views.reports, name='reports'),

    path('transactions/<int:transaction_id>/print-receipt/', views.print_receipt, name='print_receipt'),
    path('transactions/<int:transaction_id>/view-receipt/', views.view_receipt, name='view_receipt'),
    path('transactions/<int:transaction_id>/view-receipt/pdf/', views.view_receipt, {'format': 'pdf'}, name='view_receipt_pdf'),
    path('transactions/<int:transaction_id>/download-receipt/', views.download_receipt_pdf, name='download_receipt_pdf'),
    
    path('deposits/<int:deposit_id>/view-receipt/', views.view_deposit_receipt, name='view_deposit_receipt'),
    path('deposits/<int:deposit_id>/print-receipt/', views.print_deposit_receipt, name='print_deposit_receipt'),
    path('adjustments/<int:adjustment_id>/view-receipt/', views.view_adjustment_receipt, name='view_adjustment_receipt'),

    path('clients/create/', views.create_client, name='create_client'),
    path('clients/<int:client_id>/', views.view_client, name='view_client'),
    path('clients/<int:client_id>/adjust-balance/', views.adjust_client_balance, name='adjust_client_balance'),
    path('clients/', views.clients_list, name='clients_list'),
    path('clients/<int:client_id>/edit/', views.edit_client, name='edit_client'),
    path('clients/<int:client_id>/delete/', views.delete_client, name='delete_client'),

]