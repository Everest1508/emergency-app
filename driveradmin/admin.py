from django.contrib import admin
from .models import UserStatusHistory, UserOnDutyHistory

class UserStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('user__username',)

admin.site.register(UserStatusHistory, UserStatusHistoryAdmin)
admin.site.register(UserOnDutyHistory)
