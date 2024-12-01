# Django

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse
from django.views import View
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import ProjectForm, ProjectControlForm, EvidenceForm
from django.http import JsonResponse
from django.template.loader import render_to_string

# Hashing Lib
import hashlib

# My Models
from .models import (
    ProjectMembership,
    Project,
    Subdomain,
    Domain,
    Control,
    Evidence,
    ProjectControl,
    Invitation,
)

# UUID Package
import uuid

# weasyprint
from weasyprint import HTML


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


class ProjectControlEditView(LoginRequiredMixin, UpdateView):
    model = ProjectControl
    template_name = "project_control_edit.html"
    fields = ["notes", "status", "risk"]
    context_object_name = "project_control"

    def get_success_url(self):
        # Redirect back to the project control list view for the subdomain and project
        project_id = self.object.project.id
        subdomain_id = self.object.control.subdomain.id
        return reverse_lazy(
            "project_control_list",
            kwargs={"project_id": project_id, "subdomain_id": subdomain_id},
        )


class EvidenceListView(LoginRequiredMixin, ListView):
    model = Evidence
    template_name = "evidence_list.html"
    context_object_name = "evidences"

    def get_queryset(self):
        # Fetch the ProjectControl object based on the provided primary key (pk)
        project_control = ProjectControl.objects.get(pk=self.kwargs["pk"])
        # Return all related evidence objects using the `evidences` related_name
        return project_control.evidences.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project_control"] = ProjectControl.objects.get(pk=self.kwargs["pk"])
        return context


class ProjectManagementView(TemplateView):
    template_name = "project_management.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = kwargs.get("project_id")

        # Get the project
        project = get_object_or_404(Project, id=project_id)
        context["project"] = project

        subdomain_progress = []

        # Iterate through each domain in the project
        for domain in project.domains.all():
            domain_subdomain_progress = []

            # Iterate through subdomains related to the current domain
            for subdomain in domain.subdomains.all():
                controls = ProjectControl.objects.filter(
                    project=project, control__subdomain=subdomain
                )
                total_controls = controls.count()
                completed_controls = controls.filter(status="Complete").count()
                progress_percentage = (
                    (completed_controls / total_controls) * 100
                    if total_controls > 0
                    else 0
                )

                domain_subdomain_progress.append(
                    {
                        "subdomain": subdomain,
                        "completed_controls": completed_controls,
                        "total_controls": total_controls,
                        "progress": progress_percentage,
                    }
                )

            # Add the subdomain progress for this domain
            subdomain_progress.append(
                {
                    "domain": domain,
                    "subdomain_progress": domain_subdomain_progress,
                }
            )

        context["subdomain_progress"] = subdomain_progress

        # Get project members
        members = ProjectMembership.objects.filter(project=project)
        context["members"] = members

        return context


class ManageMembersView(LoginRequiredMixin, TemplateView):
    template_name = "manage_members.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = kwargs.get("project_id")

        # Get the project
        project = get_object_or_404(Project, id=project_id)
        context["project"] = project

        # Get project members
        members = ProjectMembership.objects.filter(project=project, role="Auditor")
        context["members"] = members

        return context

    def post(self, request, *args, **kwargs):
        project_id = kwargs.get("project_id")
        project = get_object_or_404(Project, id=project_id)

        # Handle removing a member
        if "user_id" in request.POST:
            user_id = request.POST.get("user_id")
            membership = ProjectMembership.objects.filter(
                user_id=user_id, project=project
            ).first()
            if membership:
                membership.delete()
                return JsonResponse({"status": "success", "message": "Member removed."})
            else:
                return JsonResponse(
                    {"status": "error", "message": "Membership not found."}
                )

        # Handle generating an invitation link
        elif "generate_invitation" in request.POST:
            token = uuid.uuid4().hex
            Invitation.objects.create(
                token=token, project=project, invited_by=request.user
            )
            invitation_link = request.build_absolute_uri(
                reverse("handle_invitation", kwargs={"token": token})
            )
            return JsonResponse({"status": "success", "link": invitation_link})

        return JsonResponse({"status": "error", "message": "Invalid request."})


@login_required
def handle_invitation(request, token):
    # Retrieve the invitation or return a 404 if not found
    invitation = get_object_or_404(Invitation, token=token)

    # Check if the invitation is already used or expired
    if not invitation.is_valid():
        return render(request, "invitation_invalid.html")  # Display an error page

    # Check if the user is already a member of the project
    existing_membership = ProjectMembership.objects.filter(
        user=request.user, project=invitation.project
    ).exists()
    if existing_membership:
        invitation.status = "Used"
        invitation.save()

        return redirect(
            "overview", invitation.project.id
        )  # Redirect to the overview if already a member

    if request.method == "POST":
        if "accept" in request.POST:
            # Add the user to the project as an Auditor
            ProjectMembership.objects.create(
                user=request.user,
                project=invitation.project,
                role="Auditor",
            )
            # Mark the invitation as used
            invitation.status = "Used"
            invitation.save()

            # Redirect to the project overview
            return redirect("overview", invitation.project.id)
        elif "reject" in request.POST:
            # Optionally mark the invitation as "Rejected" or just leave it as is
            invitation.status = "Rejected"
            invitation.save()
            return redirect("home")  # Redirect to the home page or a different page

    # Render the invitation acceptance/rejection page
    return render(request, "handle_invitation.html", {"invitation": invitation})


def generate_project_report(request, project_id):
    # Fetch the project and its memberships
    project = Project.objects.get(id=project_id)
    project_members = ProjectMembership.objects.filter(project=project)

    # Prepare a dictionary for domains with their subdomains classified as audited or unaudited
    domain_subdomains = {}

    # Loop through the project's domains and subdomains
    for domain in project.domains.all():
        # Initialize a dictionary to hold audited and unaudited subdomains for this domain
        audited_subdomains = []
        unaudited_subdomains = []

        for subdomain in domain.subdomains.all():
            # Fetch all ProjectControl objects (both "Complete" and "Incomplete") for the subdomain
            project_controls = ProjectControl.objects.filter(
                control__subdomain=subdomain, project=project
            )

            # Check if all controls are complete
            all_complete = all(
                control.status == "Complete" for control in project_controls
            )

            # Classify the subdomain as audited or unaudited
            if project_controls.exists():
                audited_subdomains.append(
                    {
                        "subdomain": subdomain,
                        "project_controls": project_controls,
                        "all_complete": all_complete,  # Pass the completeness status
                    }
                )
            else:
                unaudited_subdomains.append(
                    {
                        "subdomain": subdomain,
                        "project_controls": [],
                        "all_complete": False,  # Mark as incomplete if not audited
                    }
                )

        # Add both audited and unaudited subdomains to the domain's entry in the dictionary
        domain_subdomains[domain] = {
            "audited_subdomains": audited_subdomains,
            "unaudited_subdomains": unaudited_subdomains,
        }

    # Render the HTML content with the context data
    html_content = render_to_string(
        "project_report.html",
        {
            "project": project,
            "project_members": project_members,
            "domain_subdomains": domain_subdomains,
        },
    )

    # Convert the HTML to PDF using WeasyPrint
    pdf_file = HTML(string=html_content).write_pdf()

    # Create a response with the PDF file
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{project.title}_report.pdf"'
    )

    return response
