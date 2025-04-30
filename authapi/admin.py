from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User,EmailGroupModel,CarPic
from django.contrib import messages
from utils.email import send_dynamic_email

@admin.action(description="Send account verified email to selected users")
def send_verified_email_action(modeladmin, request, queryset):
    # Filter only verified users
    verified_users = queryset.filter(is_verified=False)

    # Check if there are verified users in the selection
    if not verified_users.exists():
        messages.warning(request, "Verified users selected.")
        return

    try:
        email_template = EmailGroupModel.objects.get(type="driver-verified")
    except EmailGroupModel.DoesNotExist:
        messages.error(request, "Email template for account verification not found.")
        return

    for user in verified_users:
        try:
            context_data = {
                "username":user.first_name,
            }
            email_response = send_dynamic_email(
                    subject=email_template.subject,
                    from_email=email_template.from_email,
                    recipient_email=user.email,
                    body_template=email_template.body_template,
                    context_data=context_data,
                )
            
            if email_response["status"] == "error":
                messages.error(request, f"Failed to send email to {user.email}: {str(e)}")
                continue
            
            user.is_verified = True
            user.save()
        except Exception as e:
            messages.error(request, f"Failed to send email to {user.email}: {str(e)}")
            continue

    messages.success(request, "Verification emails sent successfully to selected users.")
    
@admin.action(description="Send account remark to selected users")
def send_remark_email_action(modeladmin, request, queryset):
    # Filter only verified users
    verified_users = queryset.filter(is_verified=False)

    # Check if there are verified users in the selection
    if not verified_users.exists():
        messages.warning(request, "Verified users selected.")
        return

    try:
        email_template = EmailGroupModel.objects.get(type="driver-remark")
    except EmailGroupModel.DoesNotExist:
        messages.error(request, "Email template for account verification not found.")
        return

    for user in verified_users:
        try:
            context_data = {
                "username":user.first_name,
                "remark":user.remark
            }
            email_response = send_dynamic_email(
                    subject=email_template.subject,
                    from_email=email_template.from_email,
                    recipient_email=user.email,
                    body_template=email_template.body_template,
                    context_data=context_data,
                )
            
            if email_response["status"] == "error":
                messages.error(request, f"Failed to send email to {user.email}: {str(e)}")
                continue
            
            user.delete()
        except Exception as e:
            messages.error(request, f"Failed to send email to {user.email}: {str(e)}")
            continue

    messages.success(request, "Verification emails sent successfully to selected users.")

class CarPicInline(admin.TabularInline):
    model = CarPic
    extra = 1


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type',"type",'phone_number', 'is_staff', 'is_active')
    list_filter = ('user_type', 'is_staff', 'is_active',"is_verified")
    inlines = [CarPicInline,]
    
    fieldsets = (
        (None, {'fields': ('username', 'password','added_by')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number','license_pic','type','driver_pic', 'user_type',"remark","verification_status","device_id")}),
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
    actions = [send_verified_email_action,send_remark_email_action,]

admin.site.register(User, CustomUserAdmin)
admin.site.register(EmailGroupModel)