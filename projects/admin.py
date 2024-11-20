from django.contrib import admin
from .models import (
    Domain,
    Subdomain,
    Control,
    Project,
    ProjectMembership,
    ProjectControl,
    Evidence,
)


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    readonly_fields = ("name", "description")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Subdomain)
class SubdomainAdmin(admin.ModelAdmin):
    readonly_fields = ("name", "objective", "domain")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Control)
class ControlAdmin(admin.ModelAdmin):
    readonly_fields = ("code", "description", "subdomain")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Project)
admin.site.register(ProjectMembership)
admin.site.register(ProjectControl)
admin.site.register(Evidence)
