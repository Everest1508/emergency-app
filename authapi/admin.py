from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User,EmailGroupModel,CarPic

class CarPicInline(admin.TabularInline):
    model = CarPic
    extra = 1


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type','phone_number', 'is_staff', 'is_active')
    list_filter = ('user_type', 'is_staff', 'is_active')
    inlines = [CarPicInline,]
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number','license','type','driver_pic', 'user_type')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'verification_token','forget_token', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone_number', 'password1', 'password2', 'user_type'),
        }),
    )
    search_fields = ('username', 'email', 'user_type')
    ordering = ('username',)

admin.site.register(User, CustomUserAdmin)
admin.site.register(EmailGroupModel)