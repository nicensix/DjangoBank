"""
URL configuration for admin_panel app.
"""
from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('users/', views.user_management, name='user_management'),
    path('accounts/', views.account_management, name='account_management'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('accounts/<int:account_id>/approve/', views.approve_account, name='approve_account'),
    path('accounts/<int:account_id>/freeze/', views.freeze_account, name='freeze_account'),
    path('accounts/<int:account_id>/unfreeze/', views.unfreeze_account, name='unfreeze_account'),
    path('accounts/<int:account_id>/close/', views.close_account, name='close_account'),
    path('transactions/', views.transaction_monitoring, name='transaction_monitoring'),
    path('transactions/<int:transaction_id>/flag/', views.flag_transaction, name='flag_transaction'),
    path('transactions/<int:transaction_id>/detail/', views.transaction_detail, name='transaction_detail'),
]