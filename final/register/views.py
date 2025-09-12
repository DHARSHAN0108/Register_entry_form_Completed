# --- API endpoint for reminders dashboard ---
from django.http import JsonResponse
from django.utils import timezone
from .models import Entry

def get_reminders(request):
    # Only allow authenticated receptionist
    if not request.session.get('receptionist_logged_in'):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    now = timezone.localtime(timezone.now())
    reminders = []
    for entry in Entry.objects.all().order_by('-appointment_date', '-appointment_time'):
        appt_dt = timezone.make_aware(timezone.datetime.combine(entry.appointment_date, entry.appointment_time))
        reminder_time = appt_dt - timezone.timedelta(hours=1)
        is_upcoming = (not entry.reminder_sent) and (reminder_time > now)
        reminders.append({
            'id': entry.id,
            'appointment_date': entry.appointment_date.strftime('%Y-%m-%d'),
            'appointment_time': entry.appointment_time.strftime('%H:%M'),
            'name': entry.name,
            'email': entry.email,
            'phone': entry.phone,
            'category': entry.get_category_display() if hasattr(entry, 'get_category_display') else entry.category,
            'designated_attendee': entry.get_designated_attendee_display() if hasattr(entry, 'get_designated_attendee_display') else entry.designated_attendee,
            'status': entry.status,
            'reminder_sent': entry.reminder_sent,
            'is_upcoming': is_upcoming,
        })
    return JsonResponse({'reminders': reminders})
from django.utils import timezone
# Reminder Dashboard View


from functools import wraps

def receptionist_login_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get('receptionist_id'):
            return redirect('receptionist_login')
        return view_func(request, *args, **kwargs)
    return _wrapped

from django.contrib.admin.views.decorators import staff_member_required

@receptionist_login_required
def reminder_dashboard(request):
    from .models import Entry
    now = timezone.now()
    appointments = Entry.objects.all().order_by('-appointment_date', '-appointment_time')
    reminder_data = []
    for entry in appointments:
        dt = timezone.datetime.combine(entry.appointment_date, entry.appointment_time)
        appt_time = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        # Calculate reminder time (1 hour before appointment)
        reminder_time = appt_time - timezone.timedelta(hours=1)
        reminder_data.append({
            'id': entry.id,
            'name': entry.name,
            'email': entry.email,
            'phone': entry.phone,
            'category': entry.get_category_display() if hasattr(entry, 'get_category_display') else entry.category,
            'attendee': entry.get_designated_attendee_display() if hasattr(entry, 'get_designated_attendee_display') else entry.designated_attendee,
            'date': entry.appointment_date,
            'time': entry.appointment_time,
            'status': entry.status,
            'reminder_sent': entry.reminder_sent,
            'reminder_time': reminder_time,
            'appt_time': appt_time,
        })
    return render(request, 'reminder_dashboard.html', {
        'reminder_data': reminder_data,
        'now': now,
        'receptionist_username': request.session.get('receptionist_username')
    })
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.timezone import localdate, now
from collections import defaultdict
from django.contrib.auth.hashers import check_password
from functools import wraps
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.urls import reverse
from django.db import models
import json
import uuid
from datetime import datetime

from .forms import (
    PersonalDetailsForm,
    AppointmentDetailsForm,
    ReceptionistRegisterForm,
    ReceptionistLoginForm,
    RescheduleForm,
    CheckInForm
)
from .models import Entry, ReceptionistUserAuth, CheckInOut

def receptionist_login_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get('receptionist_id'):
            return redirect('receptionist_login')
        return view_func(request, *args, **kwargs)
    return _wrapped

def admin_login_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get('is_admin'):
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return _wrapped

def send_status_email(entry, status):
    """Send email based on appointment status"""
    base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
    
    if status == 'approved':
        subject = "Appointment Approved - Confirmation"
        message = f"""
Dear {entry.name},

Great news! Your appointment has been APPROVED.

Appointment Details:
- Date: {entry.appointment_date}
- Time: {entry.appointment_time}
- Category: {entry.get_category_display()}
- Attendee: {entry.get_designated_attendee_display()}

Please arrive 15 minutes before your scheduled time.

If you need to make any changes, please contact us immediately.

Best regards,
Appointment Management Team
        """.strip()
        
    elif status == 'rejected':
        subject = "Appointment Status Update - Alternative Options Available"
        message = f"""
Dear {entry.name},

We regret to inform you that your appointment scheduled for {entry.appointment_date} at {entry.appointment_time} is not available due to scheduling conflicts.

However, we would be happy to help you reschedule at a more convenient time.

To reschedule your appointment, please visit: {base_url}/reschedule/{entry.reschedule_token}/

Alternatively, you can book a new appointment at: {base_url}/

We apologize for any inconvenience and look forward to serving you soon.

Best regards,
Appointment Management Team
        """.strip()
        
    elif status == 'rescheduled':
        subject = "Appointment Rescheduled - New Time Confirmed"
        message = f"""
Dear {entry.name},

Your appointment has been successfully rescheduled and CONFIRMED.

NEW Appointment Details:
- Date: {entry.appointment_date}
- Time: {entry.appointment_time}
- Category: {entry.get_category_display()}
- Attendee: {entry.get_designated_attendee_display()}

Previous appointment was scheduled for: {getattr(entry, 'original_date', 'N/A')} at {getattr(entry, 'original_time', 'N/A')}

If this new time is not convenient for you, you can reschedule again using this link: {base_url}/reschedule/{entry.reschedule_token}/

Please arrive 15 minutes before your scheduled time.

Best regards,
Appointment Management Team
        """.strip()
    
    try:
        send_mail(
            subject,
            message,
            getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            [entry.email],
            fail_silently=False
        )
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def send_reschedule_pending_email(entry):
    """Send email when appointment is rescheduled by receptionist but pending approval"""
    subject = "Appointment Reschedule Proposal - Pending Your Approval"
    message = f"""
Dear {entry.name},

We need to reschedule your appointment due to unforeseen circumstances.

Original Appointment:
- Date: {entry.appointment_date}
- Time: {entry.appointment_time}

Proposed New Time:
- Date: {entry.rescheduled_date}
- Time: {entry.rescheduled_time}
- Attendee: {entry.get_designated_attendee_display()}

Reason for reschedule: {entry.reschedule_reason or 'Scheduling adjustment'}

This reschedule is currently pending approval. You will receive a confirmation email once approved by our team.

If you have any concerns about the new timing, please contact us immediately.

We apologize for any inconvenience.

Best regards,
Appointment Management Team
    """.strip()
    
    try:
        send_mail(
            subject,
            message,
            getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            [entry.email],
            fail_silently=False
        )
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def step1(request):
    if request.method == 'POST':
        form = PersonalDetailsForm(request.POST)
        if form.is_valid():
            request.session['step1'] = form.cleaned_data
            return redirect('step2')
    else:
        initial = request.session.get('step1')
        form = PersonalDetailsForm(initial=initial)
    return render(request, 'step1.html', {'form': form})

def step2(request):
    step1_data = request.session.get('step1')
    if not step1_data:
        return redirect('step1')

    # Calculate max date for the template
    from datetime import date, timedelta
    today = date.today()
    max_date = today + timedelta(days=10)

    if request.method == 'POST':
        form = AppointmentDetailsForm(request.POST, request.FILES)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.name = step1_data['name']
            entry.email = step1_data['email']
            entry.phone = step1_data['phone']
            entry.category = step1_data['category']
            # Generate reschedule token
            entry.reschedule_token = str(uuid.uuid4())
            entry.save()

            subject_user = "Appointment Scheduled Successfully"
            message_user = (
                f"Hello {entry.name},\n\n"
                f"Your appointment has been scheduled and is pending review.\n"
                f"Date: {entry.appointment_date}\n"
                f"Time: {entry.appointment_time}\n\n"
                f"You will receive a confirmation email once your appointment is approved.\n\n"
                f"Thank you!"
            )
            send_mail(subject_user, message_user,
                      getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                      [entry.email], fail_silently=True)

            subject_admin = "New Appointment Booking Notification"
            message_admin = (
                f"New appointment booked by {entry.name}\n"
                f"Date: {entry.appointment_date}\n"
                f"Time: {entry.appointment_time}\n"
                f"Category: {entry.category}\n"
                f"Phone: {entry.phone}\n"
                f"Email: {entry.email}"
            )
            send_mail(subject_admin, message_admin,
                      getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                      ['dharshanjiju001@gmail.com'], fail_silently=True)

            request.session.pop('step1', None)
            return redirect('success')
    else:
        form = AppointmentDetailsForm()

    return render(request, 'step2.html', {
        'form': form,
        'max_date': max_date  # Pass max_date to template
    })

def success(request):
    return render(request, 'success.html')

def receptionist_register(request):
    if request.method == "POST":
        form = ReceptionistRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registered! Wait for admin approval before logging in.")
            return redirect('receptionist_login')
    else:
        form = ReceptionistRegisterForm()
    return render(request, 'receptionist_register.html', {'form': form})

def receptionist_login(request):
    if request.method == "POST":
        form = ReceptionistLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            try:
                rec = ReceptionistUserAuth.objects.get(username=username)
            except ReceptionistUserAuth.DoesNotExist:
                messages.error(request, "Username not found.")
                return redirect('receptionist_login')

            if not rec.is_approved:
                messages.error(request, "Your account is not approved yet. Please contact admin.")
                return redirect('receptionist_login')

            if check_password(password, rec.password):
                request.session['receptionist_id'] = rec.id
                request.session['receptionist_username'] = rec.username
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid password.")
                return redirect('receptionist_login')
    else:
        form = ReceptionistLoginForm()
    return render(request, 'receptionist_login.html', {'form': form})

def receptionist_logout(request):
    request.session.flush()
    return redirect('receptionist_login')

@receptionist_login_required
def dashboard(request):
    entries = Entry.objects.all().order_by('appointment_date', 'appointment_time')
    grouped_entries = defaultdict(list)
    for entry in entries:
        grouped_entries[entry.appointment_date].append(entry)
    grouped_entries = dict(sorted(grouped_entries.items(), key=lambda x: x[0]))
    today = localdate()

    return render(request, 'dashboard.html', {
        'grouped_entries': grouped_entries,
        'today': today,
        'receptionist_username': request.session.get('receptionist_username')
    })

def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        if username == "admin" and password == "admin123":
            request.session["is_admin"] = True
            return redirect("approval_page")
        else:
            messages.error(request, "Invalid admin credentials.")
            return redirect("admin_login")
    return render(request, "admin_login.html")

def admin_logout(request):
    request.session.flush()
    return redirect("admin_login")

@admin_login_required
def approval_page(request):
    receptionists = ReceptionistUserAuth.objects.all().order_by("-created_at")
    return render(request, "approval_page.html", {"receptionists": receptionists})

@admin_login_required
def approve_receptionist(request, pk):
    receptionist = get_object_or_404(ReceptionistUserAuth, pk=pk)
    receptionist.is_approved = True
    receptionist.save()
    messages.success(request, f"{receptionist.username} approved successfully")
    return redirect("approval_page")

@admin_login_required
def reject_receptionist(request, pk):
    receptionist = get_object_or_404(ReceptionistUserAuth, pk=pk)
    receptionist.delete()
    messages.error(request, f"{receptionist.username} rejected")
    return redirect("approval_page")

@csrf_exempt
@require_GET
def get_appointments(request):
    from .models import ATTENDEE_CHOICES
    
    entries = Entry.objects.all().order_by('appointment_date', 'appointment_time')
    
    appointments_data = []
    for entry in entries:
        appointments_data.append({
            'id': entry.id,
            'appointment_date': entry.appointment_date.strftime('%Y-%m-%d'),
            'appointment_time': entry.appointment_time.strftime('%H:%M'),
            'date': entry.appointment_date.strftime('%Y-%m-%d'),  # For backward compatibility
            'time': entry.appointment_time.strftime('%I:%M %p'),  # For backward compatibility
            'name': entry.name,
            'email': entry.email,
            'phone': entry.phone,
            'category': entry.category,
            'reason': entry.reason,
            'status': entry.status,
            'document_url': entry.document.url if entry.document else None,
            'designated_attendee': entry.designated_attendee,
            'rescheduled_date': entry.rescheduled_date.strftime('%Y-%m-%d') if entry.rescheduled_date else None,
            'rescheduled_time': entry.rescheduled_time.strftime('%H:%M') if entry.rescheduled_time else None,
            'reschedule_reason': getattr(entry, 'reschedule_reason', ''),
        })
    
    # Include attendee choices in the response
    attendee_choices = []
    for value, display_name in ATTENDEE_CHOICES:
        attendee_choices.append({
            'value': value,
            'display': display_name
        })
    
    return JsonResponse({
        'appointments': appointments_data,
        'attendee_choices': attendee_choices
    }, safe=False)

@csrf_exempt
@require_POST
def update_appointment_status(request):
    try:
        data = json.loads(request.body)
        appointment_id = data.get('id')
        new_status = data.get('status')
        
        appointment = Entry.objects.get(id=appointment_id)
        old_status = appointment.status
        appointment.status = new_status
        appointment.save()
        
        # Send email notification only if status actually changed
        if old_status != new_status:
            email_sent = send_status_email(appointment, new_status)
            if email_sent:
                return JsonResponse({'success': True, 'message': 'Status updated and email sent'})
            else:
                return JsonResponse({'success': True, 'message': 'Status updated but email failed'})
        
        return JsonResponse({'success': True, 'message': 'Status updated'})
        
    except Entry.DoesNotExist:
        return JsonResponse({'error': 'Appointment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_POST
@receptionist_login_required
def receptionist_reschedule(request):
    """Handle receptionist-initiated reschedule"""
    try:
        data = json.loads(request.body)
        appointment_id = data.get('id')
        new_date = data.get('new_date')
        new_time = data.get('new_time')
        new_attendee = data.get('new_attendee')
        reason = data.get('reason', '')
        
        appointment = Entry.objects.get(id=appointment_id)
        
        # Store original values if not already stored
        if not hasattr(appointment, 'original_date') or not appointment.original_date:
            appointment.original_date = appointment.appointment_date
            appointment.original_time = appointment.appointment_time
        
        # Update reschedule fields
        appointment.rescheduled_date = datetime.strptime(new_date, '%Y-%m-%d').date()
        appointment.rescheduled_time = datetime.strptime(new_time, '%H:%M').time()
        appointment.designated_attendee = new_attendee
        appointment.reschedule_reason = reason
        appointment.status = 'pending_reschedule'
        appointment.save()
        
        # Send notification email to user about pending reschedule
        send_reschedule_pending_email(appointment)
        
        return JsonResponse({'success': True, 'message': 'Appointment rescheduled and pending approval'})
        
    except Entry.DoesNotExist:
        return JsonResponse({'error': 'Appointment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_POST
@receptionist_login_required
def approve_reschedule(request):
    """Approve a rescheduled appointment"""
    try:
        data = json.loads(request.body)
        appointment_id = data.get('id')
        
        appointment = Entry.objects.get(id=appointment_id)
        
        if appointment.status != 'pending_reschedule':
            return JsonResponse({'error': 'Appointment is not pending reschedule'}, status=400)
        
        # Apply the reschedule
        appointment.appointment_date = appointment.rescheduled_date
        appointment.appointment_time = appointment.rescheduled_time
        appointment.status = 'rescheduled'
        appointment.save()
        
        # Send confirmation email to user
        email_sent = send_status_email(appointment, 'rescheduled')
        
        if email_sent:
            return JsonResponse({'success': True, 'message': 'Reschedule approved and email sent'})
        else:
            return JsonResponse({'success': True, 'message': 'Reschedule approved but email failed'})
        
    except Entry.DoesNotExist:
        return JsonResponse({'error': 'Appointment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def reschedule_appointment(request, token):
    """Handle user-initiated appointment rescheduling"""
    try:
        appointment = Entry.objects.get(reschedule_token=token)
    except Entry.DoesNotExist:
        messages.error(request, "Invalid or expired reschedule link.")
        return redirect('step1')
    
    if request.method == 'POST':
        form = RescheduleForm(request.POST)
        if form.is_valid():
            # Update appointment with new details
            appointment.appointment_date = form.cleaned_data['appointment_date']
            appointment.appointment_time = form.cleaned_data['appointment_time']
            appointment.designated_attendee = form.cleaned_data['designated_attendee']
            appointment.status = 'pending'  # Reset to pending for approval
            
            # Update reason if provided
            if form.cleaned_data.get('reason'):
                appointment.reason = form.cleaned_data['reason']
            
            appointment.save()
            
            # Send confirmation email
            subject = "Appointment Rescheduled Successfully"
            message = f"""
Dear {appointment.name},

Your appointment has been successfully rescheduled.

New Appointment Details:
- Date: {appointment.appointment_date}
- Time: {appointment.appointment_time}
- Category: {appointment.get_category_display()}
- Attendee: {appointment.get_designated_attendee_display()}

Your appointment is now pending approval. You will receive a confirmation email once approved.

Thank you for using our service.

Best regards,
Appointment Management Team
            """.strip()
            
            send_mail(
                subject,
                message,
                getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                [appointment.email],
                fail_silently=True
            )
            
            # Notify admin
            admin_subject = "Appointment Rescheduled - Needs Approval"
            admin_message = f"""
Appointment rescheduled by {appointment.name}

New Details:
- Date: {appointment.appointment_date}
- Time: {appointment.appointment_time}
- Category: {appointment.category}
- Phone: {appointment.phone}
- Email: {appointment.email}
- Reason: {appointment.reason}

Please review and approve.
            """.strip()
            
            send_mail(
                admin_subject,
                admin_message,
                getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                ['dharshanjiju001@gmail.com'],
                fail_silently=True
            )
            
            return render(request, 'reschedule_success.html', {'appointment': appointment})
    else:
        # Pre-populate form with existing appointment data
        initial_data = {
            'appointment_date': appointment.appointment_date,
            'appointment_time': appointment.appointment_time,
            'designated_attendee': appointment.designated_attendee,
            'reason': appointment.reason,
        }
        form = RescheduleForm(initial=initial_data)
    
    return render(request, 'reschedule.html', {
        'form': form,
        'appointment': appointment
    })

@csrf_exempt
@require_POST
def delete_appointment(request):
    """Delete appointment permanently"""
    try:
        data = json.loads(request.body)
        appointment_id = data.get('id')
        
        appointment = Entry.objects.get(id=appointment_id)
        appointment.delete()
        
        return JsonResponse({'success': True, 'message': 'Appointment deleted successfully'})
        
    except Entry.DoesNotExist:
        return JsonResponse({'error': 'Appointment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_GET
def get_attendee_choices(request):
    """Return available attendee choices from the model"""
    from .models import ATTENDEE_CHOICES
    
    attendee_data = []
    for value, display_name in ATTENDEE_CHOICES:
        attendee_data.append({
            'value': value,
            'display': display_name
        })
    
    return JsonResponse({'attendees': attendee_data}, safe=False)



def check_in_out_form(request):
    """Handle check-in form only - prevent duplicate check-ins and allow approved/rescheduled appointments"""
    checkin_form = CheckInForm()
    entry = None
    message = ""
    already_checked_in = False
    not_approved = False
    
    if request.method == 'POST':
        checkin_form = CheckInForm(request.POST)
        if checkin_form.is_valid():
            phone = checkin_form.cleaned_data['phone']
            try:
                entry = Entry.objects.get(phone=phone)
                
                # Check if appointment is approved OR rescheduled
                if entry.status not in ['approved', 'rescheduled']:
                    message = f"Cannot check-in. Appointment status is '{entry.get_status_display()}'. Only approved or rescheduled appointments can be checked in."
                    not_approved = True
                else:
                    # Check if this appointment already has a check-in record today
                    today = now().date()
                    existing_checkin = CheckInOut.objects.filter(
                        entry=entry,
                        in_time__date=today
                    ).exists()
                    
                    if existing_checkin:
                        message = "This appointment has already been checked in today."
                        already_checked_in = True
                    else:
                        # Create a new check-in record
                        CheckInOut.objects.create(
                            entry=entry,
                            in_time=now(),
                            user_remarks=checkin_form.cleaned_data['user_remarks']
                        )
                        
                        message = "Check-in successful!"
                        
            except Entry.DoesNotExist:
                message = "No appointment found with this phone number."
    
    return render(request, 'checkinout_form.html', {
        'checkin_form': checkin_form,
        'message': message,
        'entry': entry,
        'already_checked_in': already_checked_in,
        'not_approved': not_approved
    })



@receptionist_login_required
def check_in_out_report(request):
    """Display all check-in/out records"""
    records = CheckInOut.objects.select_related('entry').all().order_by('-created_at')
    
    # Filter by date if provided
    date_filter = request.GET.get('date')
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            records = records.filter(
                models.Q(created_at__date=filter_date) | 
                models.Q(in_time__date=filter_date) |
                models.Q(out_time__date=filter_date)
            )
        except ValueError:
            pass
    
    return render(request, 'checkinout_report.html', {
        'records': records,
        'receptionist_username': request.session.get('receptionist_username')
    })

@csrf_exempt
@require_POST
@receptionist_login_required
def update_checkinout_record(request):
    """API endpoint to update check-in/out records"""
    try:
        data = json.loads(request.body)
        record_id = data.get('id')
        
        # Get the record
        record = CheckInOut.objects.get(id=record_id)
        
        # Update fields based on what's provided in the request
        if 'in_time' in data:
            in_time_value = data['in_time']
            if in_time_value:
                try:
                    # Handle ISO format (from database)
                    if 'T' in in_time_value and ':' in in_time_value:
                        if in_time_value.endswith('Z'):
                            in_time_value = in_time_value.replace('Z', '+00:00')
                        record.in_time = datetime.fromisoformat(in_time_value)
                    else:
                        # Handle datetime-local format (YYYY-MM-DDTHH:MM)
                        record.in_time = datetime.strptime(in_time_value, '%Y-%m-%dT%H:%M')
                except (ValueError, TypeError) as e:
                    return JsonResponse({'error': f'Invalid in_time format: {str(e)}'}, status=400)
            else:
                record.in_time = None
        
        if 'out_time' in data:
            out_time_value = data['out_time']
            if out_time_value:
                try:
                    # Handle ISO format (from database)
                    if 'T' in out_time_value and ':' in out_time_value:
                        if out_time_value.endswith('Z'):
                            out_time_value = out_time_value.replace('Z', '+00:00')
                        record.out_time = datetime.fromisoformat(out_time_value)
                    else:
                        # Handle datetime-local format (YYYY-MM-DDTHH:MM)
                        record.out_time = datetime.strptime(out_time_value, '%Y-%m-%dT%H:%M')
                except (ValueError, TypeError) as e:
                    return JsonResponse({'error': f'Invalid out_time format: {str(e)}'}, status=400)
            else:
                record.out_time = None
        
        if 'user_remarks' in data:
            record.user_remarks = data['user_remarks']
        
        if 'attendee_remarks' in data:
            record.attendee_remarks = data['attendee_remarks']
        
        record.save()
        
        return JsonResponse({'success': True, 'message': 'Record updated successfully'})
        
    except CheckInOut.DoesNotExist:
        return JsonResponse({'error': 'Record not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_GET
@receptionist_login_required
def get_checkinout_records(request):
    """API endpoint to fetch check-in/out records"""
    try:
        # Get date filter if provided
        date_filter = request.GET.get('date')
        
        # Get all records with related entry data
        records = CheckInOut.objects.select_related('entry').all().order_by('-created_at')
        
        # Apply date filter if provided
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                records = records.filter(
                    models.Q(created_at__date=filter_date) | 
                    models.Q(in_time__date=filter_date) |
                    models.Q(out_time__date=filter_date)
                )
            except ValueError:
                # If date format is invalid, ignore the filter
                pass
        
        # Prepare response data
        records_data = []
        for record in records:
            records_data.append({
                'id': record.id,
                'entry': {
                    'id': record.entry.id,
                    'name': record.entry.name,
                    'phone': record.entry.phone,
                    'email': record.entry.email,
                },
                'in_time': record.in_time.isoformat() if record.in_time else None,
                'out_time': record.out_time.isoformat() if record.out_time else None,
                'user_remarks': record.user_remarks or '',
                'attendee_remarks': record.attendee_remarks or '',
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'records': records_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    
# views.py - Add this function

@csrf_exempt
@require_POST
@receptionist_login_required
def process_checkout(request):
    """Process checkout form submission"""
    try:
        appointment_id = request.POST.get('appointment_id')
        attendee_remarks = request.POST.get('attendee_remarks', '')
        
        # Get the latest check-in record for this appointment
        checkin_record = CheckInOut.objects.filter(
            entry_id=appointment_id
        ).order_by('-created_at').first()
        
        if checkin_record:
            # Update check-out time and remarks
            checkin_record.out_time = now()
            checkin_record.attendee_remarks = attendee_remarks
            checkin_record.save()
            
            return JsonResponse({
                'success': True, 
                'message': 'Check-out completed successfully'
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': 'No check-in record found for this appointment'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=400)