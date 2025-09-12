from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from register.models import Entry
from datetime import timedelta

def send_appointment_reminders():
    now = timezone.now()
    one_hour_later = now + timedelta(hours=1)
    entries = Entry.objects.filter(status__in=['approved', 'rescheduled'], reminder_sent=False)
    print(f"[DEBUG] Now: {now}")
    print(f"[DEBUG] One hour later: {one_hour_later}")
    print(f"[DEBUG] Found {entries.count()} approved or rescheduled appointments with reminder_sent=False")
    for entry in entries:
        dt = timezone.datetime.combine(entry.appointment_date, entry.appointment_time)
        appointment_datetime = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        print(f"[DEBUG] Checking appointment for {entry.email} at {appointment_datetime} (reminder_sent={entry.reminder_sent})")
        if now < appointment_datetime <= one_hour_later:
            print(f"[DEBUG] Appointment is within the next hour. Attempting to send reminder...")
            subject = 'Appointment Reminder'
            message = f"""
Dear {entry.name},

This is a reminder that you have an appointment scheduled.

Appointment Details:
- Name: {entry.name}
- Email: {entry.email}
- Phone: {entry.phone}
- Category: {entry.get_category_display() if hasattr(entry, 'get_category_display') else entry.category}
- Attendee: {entry.get_designated_attendee_display() if hasattr(entry, 'get_designated_attendee_display') else entry.designated_attendee}
- Date: {entry.appointment_date}
- Time: {entry.appointment_time}
- Reason: {entry.reason}

Please arrive 15 minutes before your scheduled time.
If you need to make any changes, please contact us immediately.

Thank you!
"""
            try:
                send_mail(
                    subject,
                    message,
                    getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                    [entry.email],
                    fail_silently=False
                )
                entry.reminder_sent = True
                entry.save()
                print(f"[SUCCESS] Reminder sent to {entry.email} for appointment at {entry.appointment_date} {entry.appointment_time}")
            except Exception as e:
                print(f"[ERROR] Failed to send reminder to {entry.email}: {e}")
        else:
            print(f"[DEBUG] No reminder sent for {entry.email}: now={now}, appointment_datetime={appointment_datetime}, reminder_sent={entry.reminder_sent}")
