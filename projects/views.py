from django.shortcuts import render, redirect, get_object_or_404
from .models import ProjectMembership, Project, Subdomain, Domain
from django.urls import reverse
from django.views import View
from django.views.generic import ListView
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import ProjectForm
from django.http import JsonResponse


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


class DomainSelectionView(View):
    def get(self, request, project_id):
        # Get the project and its domains
        project = get_object_or_404(Project, id=project_id)
        domains = project.domains.all()  # Get predefined domains for the project
        return render(
            request, "domain_selection.html", {"project": project, "domains": domains}
        )

    def post(self, request, project_id):
        # Get the selected domain and subdomain
        subdomain_id = request.POST.get("subdomain")

        subdomain = get_object_or_404(Subdomain, id=subdomain_id)

        # Redirect to the audit page with the selected domain and subdomain
        return redirect("audit_start", project_id=project_id, subdomain_id=subdomain.id)


def get_subdomains(request, domain_id):
    try:
        domain = Domain.objects.get(id=domain_id)
        subdomains = domain.subdomains.all()
        data = {
            "subdomains": [
                {"id": subdomain.id, "name": subdomain.name} for subdomain in subdomains
            ]
        }
        return JsonResponse(data)
    except Domain.DoesNotExist:
        return JsonResponse({"error": "Domain not found."}, status=404)


class AuditStartView(View):
    def get(self, request, project_id, subdomain_id):
        pass

    def post(self, request, project_id, subdomain_id):
        pass
