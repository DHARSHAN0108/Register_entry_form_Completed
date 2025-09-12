from django.apps import AppConfig


from django.apps import AppConfig
import threading
import time

class RegisterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'register'

    def ready(self):
        from register.reminder_utils import send_appointment_reminders

        def reminder_loop():
            while True:
                try:
                    send_appointment_reminders()
                except Exception as e:
                    print(f"Reminder thread error: {e}")
                time.sleep(30)  # 30 seconds

        t = threading.Thread(target=reminder_loop, daemon=True)
        t.start()