"""
URL configuration for transactions app.
"""
from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('deposit/', views.deposit_view, name='deposit'),
    path('withdrawal/', views.withdrawal_view, name='withdrawal'),
    path('transfer/', views.transfer_view, name='transfer'),
    path('history/', views.transaction_history_view, name='history'),
    path('statement/csv/', views.download_csv_statement, name='download_csv_statement'),
    path('statement/pdf/', views.download_pdf_statement, name='download_pdf_statement'),
]