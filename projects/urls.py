from django.urls import path
from .views import ProjectListView, ProjectCreateView

urlpatterns = [
    path("project_list/", ProjectListView.as_view(), name="project_list"),
    path("project_new/", ProjectCreateView.as_view(), name="project_create"),
]
