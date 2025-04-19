from django.core.mail import send_mail, EmailMessage, get_connection
from django.template import Template, Context
from django.conf import settings
from .models import EmailAccount  

def send_dynamic_email(subject, from_email, recipient_email, body_template, context_data):
    """
    Send an email using either an active EmailAccount or Django default email settings.
    """
    try:
        # Render the email body
        template = Template(body_template)
        context = Context(context_data)
        rendered_body = template.render(context)

        # Try to use an active email account
        email_account = EmailAccount.objects.filter(is_active=True).first()

        if email_account:
            # Use custom SMTP credentials from the model
            connection = get_connection(
                host='smtp.gmail.com',  # or your provider
                port=587,
                username=email_account.email,
                password=email_account.app_password,
                use_tls=True
            )

            email = EmailMessage(
                subject=subject,
                body=rendered_body,
                from_email=email_account.email,
                to=recipient_email.split(','),
                connection=connection
            )
        else:
            # Fallback to default Django email backend
            email = EmailMessage(
                subject=subject,
                body=rendered_body,
                from_email=from_email or settings.EMAIL_HOST_USER,
                to=recipient_email.split(',')
            )

        email.send()
        return {"status": "success", "message": "Email sent successfully."}

    except Exception as e:
        return {"status": "error", "message": str(e)}
