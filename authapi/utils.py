import random
import string

from utils.email import send_dynamic_email


def generate_unique_username():
    from .models import User
    while True:
        username = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        if not User.objects.filter(username=username).exists():
            return username
        
def get_key_from_cookies(scope,key):
    headers = scope.get('headers', [])

    cookie_header = None
    for name, value in headers:
        if name.lower() == b'cookie':
            cookie_header = value.decode('utf-8')
            break

    if cookie_header:
        cookies = cookie_header.split(';')
        for cookie in cookies:
            cookie = cookie.strip()
            if cookie.startswith(f'{key}='):
                return cookie.split('=')[1]
    return None



def send_verified_email_to_user(user):
    from .models import EmailGroupModel
    if user.is_verified:
        return {"status": "skipped", "message": f"{user.email} is already verified."}

    try:
        email_template = EmailGroupModel.objects.get(type="driver-verified")
    except EmailGroupModel.DoesNotExist:
        return {"status": "error", "message": "Email template for account verification not found."}

    context_data = {
        "username": user.first_name,
    }

    try:
        email_response = send_dynamic_email(
            subject=email_template.subject,
            from_email=email_template.from_email,
            recipient_email=user.email,
            body_template=email_template.body_template,
            context_data=context_data,
        )

        if email_response["status"] == "error":
            return {"status": "error", "message": f"Failed to send email to {user.email}"}

        user.is_verified = True
        user.save()
        return {"status": "success", "message": f"Verification email sent to {user.email}"}
    except Exception as e:
        return {"status": "error", "message": f"Exception while sending to {user.email}: {str(e)}"}

def send_remark_email_to_user(user):
    from .models import EmailGroupModel
    if user.is_verified:
        return {"status": "skipped", "message": f"{user.email} is already verified."}

    try:
        email_template = EmailGroupModel.objects.get(type="driver-remark")
    except EmailGroupModel.DoesNotExist:
        return {"status": "error", "message": "Email template for driver remark not found."}

    context_data = {
        "username": user.first_name,
        "remark": user.remark,
    }

    try:
        email_response = send_dynamic_email(
            subject=email_template.subject,
            from_email=email_template.from_email,
            recipient_email=user.email,
            body_template=email_template.body_template,
            context_data=context_data,
        )

        if email_response["status"] == "error":
            return {"status": "error", "message": f"Failed to send email to {user.email}"}

        user.delete()
        return {"status": "success", "message": f"Remark email sent and user {user.email} deleted."}
    except Exception as e:
        return {"status": "error", "message": f"Exception while sending to {user.email}: {str(e)}"}
