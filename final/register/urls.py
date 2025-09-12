# urls.py
from django.urls import path

from . import views

urlpatterns = [
    # User appointment booking flow
    path('', views.step1, name='step1'),
    path('step2/', views.step2, name='step2'),
    path('success/', views.success, name='success'),
    
    # User reschedule
    path('reschedule/<str:token>/', views.reschedule_appointment, name='reschedule_appointment'),
    
    # Receptionist authentication
    path('receptionist/register/', views.receptionist_register, name='receptionist_register'),
    path('receptionist/login/', views.receptionist_login, name='receptionist_login'),
    path('reminder-dashboard/', views.reminder_dashboard, name='reminder_dashboard'),
    path('get_reminders/', views.get_reminders, name='get_reminders'),
    path('receptionist/logout/', views.receptionist_logout, name='receptionist_logout'),
    
    # Receptionist dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Admin panel
    path('admin-login/', views.admin_login, name='admin_login'),
    path('admin-logout/', views.admin_logout, name='admin_logout'),
    path('approval/', views.approval_page, name='approval_page'),
    path('approve/<int:pk>/', views.approve_receptionist, name='approve_receptionist'),
    path('reject/<int:pk>/', views.reject_receptionist, name='reject_receptionist'),

# urls.py - Add this path
    path('process_checkout/', views.process_checkout, name='process_checkout'),
    
    
    # API endpoints for dashboard
    path('get_appointments/', views.get_appointments, name='get_appointments'),
    path('update_appointment_status/', views.update_appointment_status, name='update_appointment_status'),
    path('delete_appointment/', views.delete_appointment, name='delete_appointment'),
    
    # New receptionist reschedule endpoints
    path('receptionist_reschedule/', views.receptionist_reschedule, name='receptionist_reschedule'),
    path('approve_reschedule/', views.approve_reschedule, name='approve_reschedule'),

    path('get_attendee_choices/', views.get_attendee_choices, name='get_attendee_choices'),
    # Add these to your existing urlpatterns in urls.py

    path('checkinout/', views.check_in_out_form, name='checkinout_form'),
    path('get_checkinout_records/', views.get_checkinout_records, name='get_checkinout_records'),
    
]