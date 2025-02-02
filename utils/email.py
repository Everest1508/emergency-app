from django.core.mail import send_mail
from django.template import Template, Context

def send_dynamic_email(subject, from_email, recipient_email, body_template, context_data):
    """
    Send an email using the provided data.

    :param subject: The subject of the email.
    :param from_email: The sender's email address.
    :param recipient_email: The recipient's email address.
    :param body_template: The email body template (can include placeholders for dynamic content).
    :param context_data: A dictionary containing context for the email template.
    :return: A dictionary indicating the status and message of the email operation.
    """
    try:
        # Render the email body with the provided context data
        template = Template(body_template)
        context = Context(context_data)
        rendered_body = template.render(context)

        # Send the email
        send_mail(
            subject,
            rendered_body,
            from_email,
            [recipient_email],
            fail_silently=False,
        )
        return {"status": "success", "message": "Email sent successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
