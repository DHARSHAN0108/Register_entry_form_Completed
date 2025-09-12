from django.core.management.base import BaseCommand
from register.reminder_utils import send_appointment_reminders

class Command(BaseCommand):
    help = 'Send reminder emails for approved appointments 1 hour before the appointment time, with debug output.'

    def handle(self, *args, **kwargs):
        print('Running reminder check...')
        send_appointment_reminders()
        print('Reminder check complete.')
