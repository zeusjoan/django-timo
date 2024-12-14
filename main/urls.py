from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('export/dashboard/', views.export_dashboard_data, name='export_dashboard'),
    
    # Zamówienia
    path('zamowienia/', views.order_list, name='order_list'),
    path('zamowienia/dodaj/', views.order_create, name='order_create'),
    path('zamowienia/<int:order_id>/', views.order_detail, name='order_detail'),
    path('zamowienia/<int:order_id>/edytuj/', views.order_edit, name='order_edit'),
    path('zamowienia/<int:order_id>/usun/', views.order_delete, name='order_delete'),
    path('zamowienia/<int:order_id>/status/<str:new_status>/', views.order_status_change, name='order_status_change'),
    path('zamowienia/<int:order_id>/pdf/', views.order_pdf, name='order_pdf'),
    path('zamowienia/<int:order_id>/pdf/preview/', views.order_pdf_preview, name='order_pdf_preview'),
    path('zamowienia/<int:order_id>/zakoncz/', views.order_complete, name='order_complete'),
    path('zamowienia/<int:order_id>/aktywuj/', views.order_reactivate, name='order_reactivate'),
    
    # Rozliczenia miesięczne
    path('rozliczenia/', views.monthly_report_list, name='monthly_report_list'),
    path('rozliczenie/nowe/', views.monthly_report_create, name='monthly_report_create'),
    path('rozliczenie/<int:report_id>/', views.monthly_report_detail, name='monthly_report_detail'),
    path('rozliczenie/<int:report_id>/edytuj/', views.monthly_report_edit, name='monthly_report_edit'),
    path('rozliczenie/<int:report_id>/usun/', views.monthly_report_delete, name='monthly_report_delete'),
    path('rozliczenie/<int:report_id>/merge/', views.generate_merged_document, name='generate_merged_document'),
    path('rozliczenie/<int:report_id>/status/<str:new_status>/', views.monthly_report_status_change, name='monthly_report_status_change'),
    path('rozliczenie/<int:report_id>/zatwierdz/', views.monthly_report_approve, name='monthly_report_approve'),
    
    # Nadgodziny
    path('nadgodziny/', views.overtime_list, name='overtime_list'),
    path('nadgodziny/nowe/', views.overtime_create, name='overtime_create'),
    path('nadgodziny/<int:overtime_id>/', views.overtime_detail, name='overtime_detail'),
    path('nadgodziny/<int:overtime_id>/edytuj/', views.overtime_edit, name='overtime_edit'),
    path('nadgodziny/<int:overtime_id>/usun/', views.overtime_delete, name='overtime_delete'),
    path('nadgodziny/<int:overtime_id>/status/<str:new_status>/', views.overtime_status_change, name='overtime_status_change'),
    
    # PDF viewer
    path('pdf/<str:model_name>/<int:object_id>/<str:field_name>/', views.view_pdf, name='view_pdf'),
    
    # Profile management
    path('profil/', views.profile_view, name='profile'),
    path('zmien-haslo/', views.change_password, name='change_password'),
]
