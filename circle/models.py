from django.db import models
from member.models import Member
from app_utility import sms_utils


CIRCLE_TYPE = (
    ('PRIVATE', 'Private circle'),
    ('OPEN', 'Open circle')
)

INVITE_STATUS = (
    ('Accepted','Accepted'),
    ('Pending','Pending'),
    ('Declined','Declined')
)


class Circle(models.Model):
    circle_name = models.CharField(max_length=100,blank=False,unique=True)
    circle_type = models.CharField(max_length=10, blank=False, choices=CIRCLE_TYPE)
    circle_acc_number = models.CharField(max_length=10, blank=False, unique=True)
    initiated_by = models.ForeignKey(Member,null=False, blank=False)
    time_initiated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False)
    annual_interest_rate = models.DecimalField(max_digits=5, decimal_places=3, default=0.000)
    minimum_share = models.IntegerField(default=200)

    class Meta:
        db_table = 'Circle'




class CircleMember(models.Model):
    circle = models.ForeignKey(Circle, null=False, blank=False)
    member = models.ForeignKey(Member, null=False, blank=False)
    allow_public_guarantees_request = models.BooleanField(default=True)
    time_joined = models.DateTimeField(null=False, auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'CircleMember'
        unique_together = ("circle", "member")

class CircleInvitation(models.Model):
    invited_by = models.ForeignKey(CircleMember, null=False, blank=False)
    is_member = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, blank=True)
    time_invited = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10,default='Pending',choices=INVITE_STATUS)

    class Meta:
        db_table = 'CircleInvitation'

    def save(self,*args,**kwargs):
        if Member.objects.filter(phone_number=self.phone_number).exists():
            self.is_member = True
        super(CircleInvitation,self).save()



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
