import random
import string
from .models import User

def generate_unique_username():
    while True:
        username = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        if not User.objects.filter(username=username).exists():
            return username