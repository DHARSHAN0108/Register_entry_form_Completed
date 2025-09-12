from django.db import models
from django.contrib.auth.hashers import make_password
from django.utils import timezone

# Category, Attendee, and Status choices
CATEGORY_CHOICES = [
    ('student', 'Student'),
    ('staff', 'Staff'),
    ('employee', 'Employee'),
    ('intern', 'Intern'),
]

ATTENDEE_CHOICES = [
    ('member1', 'Member 1'),
    ('member2', 'Member 2'),
]

STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('rescheduled', 'Rescheduled'),
    ('completed', 'Completed'),
    ('pending_reschedule', 'Pending Reschedule'),
]


# Appointment Entry model
class Entry(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15, unique=True)
    reason = models.TextField()

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    designated_attendee = models.CharField(max_length=50, choices=ATTENDEE_CHOICES)

    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    document = models.FileField(upload_to='documents/', blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reschedule_token = models.CharField(max_length=100, blank=True, null=True, unique=True)

    # Reschedule tracking
    original_date = models.DateField(blank=True, null=True)
    original_time = models.TimeField(blank=True, null=True)
    rescheduled_date = models.DateField(blank=True, null=True)
    rescheduled_time = models.TimeField(blank=True, null=True)
    reschedule_reason = models.TextField(blank=True, null=True)
    reminder_sent = models.BooleanField(default=False, help_text="Whether reminder email was sent for this appointment.")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} {self.appointment_date} {self.appointment_time} ({self.status})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Appointment Entry'
        verbose_name_plural = 'Appointment Entries'


# Receptionist model for login/authentication
class ReceptionistUserAuth(models.Model):
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)  # Hashed password
    email = models.EmailField(blank=True, null=True)
    full_name = models.CharField(max_length=100, blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        # Only hash if it's not already hashed
        if not self.password.startswith('pbkdf2_sha256$'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({'Approved' if self.is_approved else 'Pending'})"

    class Meta:
        db_table = 'receptionistuserauth'
        ordering = ['-created_at']
        verbose_name = 'Receptionist User'
        verbose_name_plural = 'Receptionist Users'


# Check-in / Check-out model
class CheckInOut(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name='checkinouts')
    in_time = models.DateTimeField(null=True, blank=True)
    out_time = models.DateTimeField(null=True, blank=True)
    user_remarks = models.TextField(blank=True, null=True)
    attendee_remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Check-in/out for {self.entry.name}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Check-in/Check-out Record'
        verbose_name_plural = 'Check-in/Check-out Records'