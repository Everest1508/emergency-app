from django.contrib import admin
from .models import *

admin.site.register(WebsiteSettings)
admin.site.register(ApplicationSettings)
admin.site.register(EmailAccount)