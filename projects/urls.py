from django.urls import path
from .views import (
    ProjectListView,
    ProjectCreateView,
    DomainSelectionView,
    AuditStartView,
    ProjectOverviewView,
    get_subdomains,
    ProjectControlListView,
    ProjectControlEditView,
    EvidenceListView,
    handle_invitation,
    ProjectManagementView,
    ManageMembersView,
)

urlpatterns = [
    path("project_list/", ProjectListView.as_view(), name="project_list"),
    path("project_new/", ProjectCreateView.as_view(), name="project_create"),
    path(
        "project_overview/<int:project_id>/",
        ProjectOverviewView.as_view(),
        name="overview",
    ),
    path(
        "project/<int:project_id>/select_domain/",
        DomainSelectionView.as_view(),
        name="domain_selection",
    ),
    path(
        "get_subdomains/<int:domain_id>/<int:project_id>/",
        get_subdomains,
        name="get_subdomains",
    ),
    path(
        "project/<int:project_id>/audit_start/<int:subdomain_id>/",
        AuditStartView.as_view(),
        name="audit_start",
    ),
    path(
        "projects/<int:project_id>/subdomains/<int:subdomain_id>/project-controls/",
        ProjectControlListView.as_view(),
        name="project_control_list",
    ),
    path(
        "project_control/edit/<int:pk>/",
        ProjectControlEditView.as_view(),
        name="project_control_edit",
    ),
    path(
        "project_control/<int:pk>/evidence/",
        EvidenceListView.as_view(),
        name="project_control_evidence",
    ),
    path("invite/<str:token>/", handle_invitation, name="handle_invitation"),
    path(
        "project/<int:project_id>/manage/",
        ProjectManagementView.as_view(),
        name="project_management",
    ),
    path(
        "project/<int:project_id>/manage/members/",
        ManageMembersView.as_view(),
        name="manage_members",
    ),
]
