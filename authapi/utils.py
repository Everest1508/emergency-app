import random
import string
from .models import User

def generate_unique_username():
    while True:
        username = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        if not User.objects.filter(username=username).exists():
            return username
        
def get_key_from_cookies(scope,key):
    # Access headers from the scope
    headers = scope.get('headers', [])

    # Find the 'cookie' header
    cookie_header = None
    for name, value in headers:
        if name.lower() == b'cookie':
            cookie_header = value.decode('utf-8')
            break

    if cookie_header:
        # Parse the session ID from the cookies
        cookies = cookie_header.split(';')
        for cookie in cookies:
            cookie = cookie.strip()
            if cookie.startswith(f'{key}='):
                return cookie.split('=')[1]
    return None

