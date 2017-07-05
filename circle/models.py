from django.db import models
from member.models import Member


class CircleType(models.Model):
    name = models.CharField(max_length=20, blank=False, unique=True)
    description = models.CharField(max_length=1000, blank=False, unique=True)
    is_public = models.BooleanField(default=False)

    class Meta:
        db_table = 'CircleType'


class Circle(models.Model):
    circle_type = models.ForeignKey(CircleType, null=False, blank=False)
    circle_acc_number = models.CharField(max_length=100, blank=False, unique=True)
    initiated_by = models.ForeignKey(Member, null=False, blank=False)
    time_initiated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    annual_interest_rate = models.DecimalField(max_digits=5, decimal_places=3, default=0.000)

    class Meta:
        db_table = 'Circle'


class CircleMember(models.Model):
    circle = models.ForeignKey(Circle, null=False, blank=False)
    member = models.ForeignKey(Member, null=False, blank=False)
    member_acc_number = models.CharField(max_length=10, null=False, blank=False)
    allow_public_guarantees_request = models.BooleanField(default=True)
    time_joined = models.DateTimeField(null=False, auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'CircleMember'


class CircleInvitation(models.Model):
    circle_member = models.ForeignKey(CircleMember, null=False, blank=False)
    invited_member = models.ForeignKey(Member, null=False, blank=False)
    phone_number = models.CharField(max_length=20, blank=True)
    time_invited = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CircleInvitation'


class CircleDirector(models.Model):
    circle_member = models.ForeignKey(CircleMember, null=False, blank=False)
    date_appointed = models.DateField(null=False)
    duration_of_tenure = models.IntegerField(null=False, blank=False, default=1)  # Duration of tenure in yrs
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'CircleDirector'


class AllowedGuarantorRequest(models.Model):
    circle_member = models.ForeignKey(CircleMember, null=False, blank=False, related_name='circle_member')
    allows_request_from = models.ForeignKey(CircleMember, null=False, blank=False, related_name='allows_request_from')
    time_created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'AllowedGuarantorRequest'





