from django.shortcuts import render
from .models import ProjectMembership, Project
from django.urls import reverse
from django.views.generic import ListView
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import ProjectForm

# Create your views here.


class ProjectListView(LoginRequiredMixin, ListView):
    model = ProjectMembership
    template_name = "project_list.html"
    context_object_name = "projectmembership_list"  # Can still be used if needed

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Projects where the user is the manager
        context["manager_projects"] = ProjectMembership.objects.filter(
            user=self.request.user, role="Manager"
        )
        # Projects where the user is a member but not a manager
        context["member_projects"] = ProjectMembership.objects.filter(
            user=self.request.user, role="Auditor"
        )
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):

    model = Project
    form_class = ProjectForm
    template_name = "project_create.html"

    def form_valid(self, form):  # new
        form.instance.created_by = self.request.user
        response = super().form_valid(form)  # Save the form and get the response

        # Add the creator as a manager of the new project
        ProjectMembership.objects.create(
            user=form.instance.created_by,
            project=form.instance,
            role="Manager",
        )

        return response

    def get_success_url(self):
        return reverse("project_list")
