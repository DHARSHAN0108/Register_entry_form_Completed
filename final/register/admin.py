from django.contrib import admin
from .models import Entry, ReceptionistUserAuth, CheckInOut


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'email', 'phone', 'category',
        'appointment_date', 'appointment_time',
        'status', 'designated_attendee'
    )
    list_filter = ('status', 'appointment_date', 'category', 'designated_attendee')
    search_fields = ('name', 'email', 'phone')


@admin.register(ReceptionistUserAuth)
class ReceptionistUserAuthAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'is_approved', 'created_at')
    list_filter = ('is_approved',)
    search_fields = ('username',)


@admin.register(CheckInOut)
class CheckInOutAdmin(admin.ModelAdmin):
    list_display = ('id', 'entry', 'in_time', 'out_time', 'user_remarks', 'attendee_remarks', 'created_at')
    list_filter = ('in_time', 'out_time')
    search_fields = ('entry__name', 'entry__phone', 'entry__email')
