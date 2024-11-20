from django.urls import path
from .views import (
    ProjectListView,
    ProjectCreateView,
    DomainSelectionView,
    AuditStartView,
    get_subdomains,
)

urlpatterns = [
    path("project_list/", ProjectListView.as_view(), name="project_list"),
    path("project_new/", ProjectCreateView.as_view(), name="project_create"),
    path(
        "project/<int:project_id>/select_domain/",
        DomainSelectionView.as_view(),
        name="domain_selection",
    ),
    path(
        "project/<int:project_id>/audit_start/<int:subdomain_id>/",
        AuditStartView.as_view(),
        name="audit_start",
    ),
    path("get-subdomains/<int:domain_id>/", get_subdomains, name="get_subdomains"),
]
