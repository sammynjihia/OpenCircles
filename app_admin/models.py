from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models

# Create your models here.


class AppAdmin(models.Model):
    user = models.OneToOneField(User, null=False, blank=False)

    class Meta:
        db_table = 'AppAdmin'






