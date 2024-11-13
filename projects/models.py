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
