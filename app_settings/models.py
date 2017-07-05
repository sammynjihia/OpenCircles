from django.db import models

# Create your models here.


class AppSetting(models.Model):
    max_num_of_circles = models.IntegerField()

    class Meta:
        db_table = 'AppSetting'


class CircleTermsOfUse(models.Model):
    term = models.CharField(max_length=200, blank=False, unique=True)
    desc = models.TextField(max_length=1500, blank=False, unique=True)
    time_added = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CircleTermsOfUse'









