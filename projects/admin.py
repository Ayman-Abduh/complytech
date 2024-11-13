from django.contrib import admin
from .models import Domain, Subdomain, Control

# Register your models here.
admin.site.register(Domain)
admin.site.register(Subdomain)
admin.site.register(Control)
