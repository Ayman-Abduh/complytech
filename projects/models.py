from django.db import models

# Create your models here.


class Domain(models.Model):

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Subdomain(models.Model):

    name = models.CharField(max_length=100, unique=True)
    objective = models.TextField(blank=True, null=True)
    domain = models.ForeignKey(
        Domain, on_delete=models.CASCADE, related_name="subdomains"
    )

    def __str__(self):
        return f"{self.domain.name} - {self.name}"


class Control(models.Model):
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    subdomain = models.ForeignKey(
        Subdomain, on_delete=models.CASCADE, related_name="controls"
    )

    def __str__(self):
        return f"{self.subdomain.name} - {self.code}"


class Project(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    scope = models.TextField()
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_finish_date = models.DateField()

    # Relationships
    created_by = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    domains = models.ManyToManyField(Domain)  # Predefined domains

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ProjectMembership(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(
        max_length=10,
        choices=[
            ("Manager", "Manager"),
            ("Auditor", "Auditor"),
        ],
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.project.title} ({self.role})"


class ProjectControl(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="project_controls"
    )
    control = models.ForeignKey(
        Control, on_delete=models.CASCADE, related_name="project_controls"
    )
    auditor = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    # Project-specific auditing information
    status = models.CharField(
        max_length=10,
        choices=[
            ("Complete", "Complete"),
            ("Incomplete", "Incomplete"),
        ],
        default="Incomplete",
    )
    notes = models.TextField(blank=True, null=True)
    risk = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.project.title} - {self.control.name}"


class Evidence(models.Model):
    project_control = models.ForeignKey(
        ProjectControl, on_delete=models.CASCADE, related_name="evidences"
    )
    document_name = models.CharField(max_length=255)
    sha_hash = models.CharField(max_length=64)  # SHA-256 hash of the document
    uploaded_by = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(blank=True, null=True)

    def __str__(self):
        return (
            f"Evidence for {self.project_control.control.name} - {self.document_name}"
        )
