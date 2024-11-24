from django.shortcuts import render, redirect, get_object_or_404
from .models import (
    ProjectMembership,
    Project,
    Subdomain,
    Domain,
    Control,
    Evidence,
    ProjectControl,
)
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.detail import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import ProjectForm, ProjectControlForm, EvidenceForm
from django.http import JsonResponse
import hashlib


# Create your views here.


class ProjectListView(LoginRequiredMixin, ListView):
    model = ProjectMembership
    template_name = "project_list.html"

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


class DomainSelectionView(LoginRequiredMixin, View):
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


def get_subdomains(request, domain_id, project_id):
    try:
        domain = Domain.objects.get(id=domain_id)

        # Get subdomains that are not audited for the specific project
        audited_subdomains = ProjectControl.objects.filter(
            project_id=project_id, control__subdomain__domain=domain
        ).values_list("control__subdomain_id", flat=True)
        subdomains = domain.subdomains.exclude(id__in=audited_subdomains)

        data = {
            "subdomains": [
                {"id": subdomain.id, "name": subdomain.name} for subdomain in subdomains
            ]
        }
        return JsonResponse(data)
    except Domain.DoesNotExist:
        return JsonResponse({"error": "Domain not found."}, status=404)


class ProjectOverviewView(LoginRequiredMixin, View):
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        domains = project.domains.all()

        domain_data = []
        for domain in domains:
            subdomain_data = []
            for subdomain in domain.subdomains.all():
                # Step 1: Get all controls related to the subdomain
                subdomain_controls = Control.objects.filter(subdomain=subdomain)

                # Step 2: Get all project controls for the current project and controls
                project_controls = ProjectControl.objects.filter(
                    project=project, control__in=subdomain_controls
                )

                # Determine the subdomain's status
                if project_controls.exists():
                    all_complete = all(
                        pc.status == "Complete" for pc in project_controls
                    )
                    status = "Complete" if all_complete else "Incomplete"
                else:
                    status = "Incomplete"

                # Check if the subdomain has been audited
                has_project_controls = project_controls.exists()

                # Get the auditor of the subdomain
                auditor = (
                    project_controls.first().auditor
                    if project_controls.exists()
                    else None
                )

                subdomain_data.append(
                    {
                        "id": subdomain.id,
                        "title": subdomain.name,
                        "status": status,
                        "auditor": auditor,
                        "has_project_controls": has_project_controls,
                    }
                )
            domain_data.append(
                {
                    "domain": domain,
                    "subdomains": subdomain_data,
                }
            )

        return render(
            request,
            "project_overview.html",
            {
                "project": project,
                "domain_data": domain_data,
            },
        )


class AuditStartView(LoginRequiredMixin, View):
    def get(self, request, project_id, subdomain_id):
        project = get_object_or_404(Project, id=project_id)
        subdomain = get_object_or_404(Subdomain, id=subdomain_id)

        # Get the current control index from the query parameter
        try:
            control_index = int(request.GET.get("control_index", 0))
        except ValueError:
            control_index = 0  # Default to the first control if conversion fails
            # Fetch all controls related to the subdomain
        controls = list(Control.objects.filter(subdomain=subdomain))

        # Check if the control_index is valid
        if control_index >= len(controls):
            # Redirect to a summary or finish page if no controls are left
            return redirect(reverse("overview", kwargs={"project_id": project.id}))

        # Get the current control
        control = controls[control_index]

        # Create forms for the control
        project_control_form = ProjectControlForm(prefix=f"control_{control.id}")
        evidence_form = EvidenceForm(prefix=f"control_evidence_{control.id}")

        return render(
            request,
            "control_auditing_page.html",
            {
                "project": project,
                "subdomain": subdomain,
                "control": control,
                "project_control_form": project_control_form,
                "evidence_form": evidence_form,
                "control_index": control_index,
                "total_controls": len(controls),
            },
        )

    def post(self, request, project_id, subdomain_id):
        project = get_object_or_404(Project, id=project_id)
        subdomain = get_object_or_404(Subdomain, id=subdomain_id)

        # Get the current control index from the query parameter
        control_index = int(request.GET.get("control_index", 0))

        # Fetch all controls related to the subdomain
        controls = list(Control.objects.filter(subdomain=subdomain))

        if control_index >= len(controls):
            # Redirect to a summary or finish page if no controls are left
            return redirect(reverse("overview", kwargs={"project_id": project.id}))

        # Get the current control
        control = controls[control_index]

        # Instantiate the forms with POST data
        project_control_form = ProjectControlForm(
            request.POST, prefix=f"control_{control.id}"
        )
        evidence_form = EvidenceForm(
            request.POST, request.FILES, prefix=f"control_evidence_{control.id}"
        )

        # Validate the forms
        if project_control_form.is_valid() and evidence_form.is_valid():
            # Save the ProjectControl instance
            project_control = project_control_form.save(commit=False)
            project_control.project = project
            project_control.control = control
            project_control.auditor = request.user
            project_control.save()

            # Check if a file was uploaded and handle it
            uploaded_file = evidence_form.cleaned_data.get("uploaded_file")
            if uploaded_file:
                document_name = uploaded_file.name

                # Calculate SHA-256 hash of the uploaded file
                sha256_hash = hashlib.sha256()
                for chunk in uploaded_file.chunks():
                    sha256_hash.update(chunk)
                sha_hash = sha256_hash.hexdigest()

                # Save the Evidence instance
                Evidence.objects.create(
                    project_control=project_control,
                    document_name=document_name,
                    sha_hash=sha_hash,
                    uploaded_by=request.user,
                )

            # Move to the next control
            next_control_index = control_index + 1
            return redirect(
                f"{reverse('audit_start', kwargs={'project_id': project_id, 'subdomain_id': subdomain_id})}?control_index={next_control_index}"
            )

        # Re-render the page with errors if the forms are invalid
        return render(
            request,
            "control_auditing_page.html",
            {
                "project": project,
                "subdomain": subdomain,
                "control": control,
                "project_control_form": project_control_form,
                "evidence_form": evidence_form,
                "control_index": control_index,
                "total_controls": len(controls),
            },
        )


class ProjectControlListView(View):
    def get(self, request, project_id, subdomain_id):
        # Fetch the project and subdomain
        project = get_object_or_404(Project, id=project_id)
        subdomain = get_object_or_404(Subdomain, id=subdomain_id)

        # Fetch all ProjectControl objects related to the given project and subdomain
        project_controls = ProjectControl.objects.filter(
            project=project, control__subdomain=subdomain
        )

        return render(
            request,
            "project_control_list.html",  # Template to display the project controls
            {
                "project": project,
                "subdomain": subdomain,
                "project_controls": project_controls,
            },
        )
