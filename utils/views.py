from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
import os

@staff_member_required  # Optional: restrict access to admin users
def log_viewer(request):
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'debug.log')

    if os.path.exists(log_path):
        with open(log_path, 'r') as file:
            content = file.read()
    else:
        content = "Log file not found."

    return HttpResponse(f"<pre style='white-space: pre-wrap;'>{content}</pre>")
