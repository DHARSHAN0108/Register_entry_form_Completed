from django import forms
from datetime import date, time as dtime, timedelta
from .models import CheckInOut, Entry, ReceptionistUserAuth
import re
from django.contrib.auth.hashers import make_password


# ---------------- Appointment Forms ---------------- #

class PersonalDetailsForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ['name', 'email', 'phone', 'category']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'yourmail@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone-number'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.label = ""
        self.fields['category'].choices = [("", "Select category")] + list(self.fields['category'].choices)

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if len(name) < 3:
            raise forms.ValidationError("Name must be at least 3 characters.")
        if not re.fullmatch(r"[A-Za-z][A-Za-z\s\-']*", name):
            raise forms.ValidationError("Name must contain only letters, spaces, hyphens or apostrophes.")
        return name

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if not phone.isdigit() or len(phone) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")

        # Prevent duplicates on new registration
        if Entry.objects.filter(phone=phone).exists():
            raise forms.ValidationError("This phone number is already registered.")

        return phone


    def clean_category(self):
        category = self.cleaned_data.get('category')
        if not category:
            raise forms.ValidationError("Please select a category.")
        return category


class AppointmentDetailsForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ['reason', 'appointment_date', 'appointment_time', 'designated_attendee', 'document']
        widgets = {
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for the visit'}),
            'appointment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'appointment_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'designated_attendee': forms.Select(attrs={'class': 'form-control'}),
            'document': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'id': 'documentInput',
                'accept': '.pdf'
            }),
        }
        help_texts = {
            'document': "Only PDF files allowed, maximum size 2MB. (Optional)"
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.label = ""
        self.fields['designated_attendee'].choices = [("", "Select attendee")] + list(self.fields['designated_attendee'].choices)
        
        # Set HTML5 min and max attributes for date field
        today = date.today()
        max_date = today + timedelta(days=10)
        self.fields['appointment_date'].widget.attrs.update({
            'min': today.strftime('%Y-%m-%d'),
            'max': max_date.strftime('%Y-%m-%d'),
        })

    def clean_appointment_date(self):
        appt_date = self.cleaned_data.get('appointment_date')
        today = date.today()
        max_date = today + timedelta(days=10)
        
        if not appt_date:
            raise forms.ValidationError("Please select an appointment date.")
        
        if appt_date < today:
            raise forms.ValidationError("Appointment date cannot be in the past.")
            
        if appt_date > max_date:
            raise forms.ValidationError(f"Appointment date cannot be more than 10 days from today. Please select a date between {today.strftime('%Y-%m-%d')} and {max_date.strftime('%Y-%m-%d')}.")
            
        return appt_date

    def clean_appointment_time(self):
        appt_time = self.cleaned_data.get('appointment_time')
        start = dtime(10, 0)
        end = dtime(22, 0)
        if not (start <= appt_time <= end):
            raise forms.ValidationError("Appointment time must be between 10:00 AM and 10:00 PM.")
        return appt_time

    def clean_document(self):
        document = self.cleaned_data.get('document')
        if document:
            if not document.name.lower().endswith('.pdf'):
                raise forms.ValidationError("Only PDF files are allowed.")
            if document.size > 2 * 1024 * 1024:
                raise forms.ValidationError("File size must be less than 2MB.")
        return document

    def clean_designated_attendee(self):
        attendee = self.cleaned_data.get('designated_attendee')
        if not attendee:
            raise forms.ValidationError("Please select an attendee.")
        return attendee


class RescheduleForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ['appointment_date', 'appointment_time', 'designated_attendee', 'reason']
        widgets = {
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Update reason for the visit (optional)'
            }),
            'appointment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'appointment_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'designated_attendee': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['appointment_date'].label = "New Appointment Date"
        self.fields['appointment_time'].label = "New Appointment Time"
        self.fields['designated_attendee'].label = "Preferred Attendee"
        self.fields['reason'].label = "Reason for Visit"
        self.fields['reason'].required = False
        
        # Set HTML5 min and max attributes for date field
        today = date.today()
        max_date = today + timedelta(days=10)
        self.fields['appointment_date'].widget.attrs.update({
            'min': today.strftime('%Y-%m-%d'),
            'max': max_date.strftime('%Y-%m-%d'),
        })

    def clean_appointment_date(self):
        appt_date = self.cleaned_data.get('appointment_date')
        today = date.today()
        max_date = today + timedelta(days=10)
        
        if not appt_date:
            raise forms.ValidationError("Please select an appointment date.")
        
        if appt_date < today:
            raise forms.ValidationError("Appointment date cannot be in the past.")
            
        if appt_date > max_date:
            raise forms.ValidationError(f"Appointment date cannot be more than 10 days from today. Please select a date between {today.strftime('%Y-%m-%d')} and {max_date.strftime('%Y-%m-%d')}.")
            
        return appt_date

    def clean_appointment_time(self):
        appt_time = self.cleaned_data.get('appointment_time')
        start = dtime(10, 0)
        end = dtime(22, 0)
        if not (start <= appt_time <= end):
            raise forms.ValidationError("Appointment time must be between 10:00 and 22:00.")
        return appt_time


# ---------------- Receptionist Auth Forms ---------------- #

class ReceptionistRegisterForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))

    class Meta:
        model = ReceptionistUserAuth
        fields = ['username', 'email', 'full_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name (optional)'}),
        }

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.password = make_password(self.cleaned_data['password1'])
        if commit:
            obj.save()
        return obj


class ReceptionistLoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))


# ---------------- Check-In Form Only ---------------- #

class CheckInForm(forms.Form):
    phone = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter your phone number', 
            'required': 'required'
        })
    )
    user_remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': 'Enter your remarks (optional)'
        })
    )

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        
        # Clean the phone number (remove spaces, dashes, etc.)
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        if len(clean_phone) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        
        # Check if an appointment exists with this phone number
        if not Entry.objects.filter(phone=clean_phone).exists():
            raise forms.ValidationError("No appointment found with this phone number.")
        
        return clean_phone