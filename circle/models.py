from django.db import models
from member.models import Member

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
    snl = 'Savings and Loans'
    intv = 'Changa'
    gl = 'Goals'
    mgr = 'Merry Go Round'
    CIRCLE_MODEL_TYPE = (
        (snl, 'Savings and Loans'),
        (intv, 'Changa'),
        (gl, 'Goals'),
        (mgr, 'Merry Go Round')
    )
    circle_name = models.CharField(max_length=100, blank=False, unique=True)
    circle_type = models.CharField(max_length=10, blank=False, choices=CIRCLE_TYPE, default='PRIVATE')
    circle_acc_number = models.CharField(max_length=10, blank=False, unique=True)
    initiated_by = models.ForeignKey(Member, null=False, blank=False)
    time_initiated = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)
    annual_interest_rate = models.DecimalField(max_digits=5, decimal_places=3, default=0.000)
    minimum_share = models.IntegerField(default=0)
    is_deactivated = models.BooleanField(default=False)
    circle_model_type = models.CharField(max_length=20, blank=False, choices=CIRCLE_MODEL_TYPE, default=snl)
    description = models.TextField(default="")

    class Meta:
        db_table = 'Circle'

class MGRCircle(models.Model):
    week = "WEEKLY"
    month = "MONTHLY"
    week_count = 7
    month_count = 30
    CYCLE_CHOICES = (
        (week_count, week),
        (month_count, month)
    )
    DAY_CHOICES = (
        ('Sunday', 'Sunday'),
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday')
    )
    circle = models.ForeignKey(Circle, null=False, blank=False, on_delete=models.CASCADE, related_name='mgr_circle')
    schedule = models.CharField(choices=CYCLE_CHOICES, max_length=20)
    amount = models.FloatField()
    fine = models.FloatField()
    day = models.CharField(choices=DAY_CHOICES, max_length=20)

    class Meta:
        db_table = 'MGRCircle'

class CircleMember(models.Model):
    circle = models.ForeignKey(Circle, null=False, blank=False)
    member = models.ForeignKey(Member, null=False, blank=False, related_name='circle_member')
    allow_public_guarantees_request = models.BooleanField(default=True)
    time_joined = models.DateTimeField(null=False, auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    priority = models.IntegerField(default=0)
    is_queueing = models.BooleanField(default=False)

    class Meta:
        db_table = 'CircleMember'
        unique_together = ("circle", "member")

class CircleMemberQueue(models.Model):
    node = models.ForeignKey(CircleMember, null=False, blank=False, related_name='current_cmq')
    next_node = models.ForeignKey(CircleMember, null=True, related_name='next_cmq')
    is_first = models.BooleanField(default=False)

    class Meta:
        db_table = 'CircleMemberQueue'

class MGRCircleCycle(models.Model):
    cycle = models.IntegerField()
    circle_member = models.ForeignKey(CircleMember, null=False, blank=False, related_name='mgr_circle_cycle')
    disbursal_date = models.DateField()
    is_complete = models.BooleanField(default=False)
    info = models.TextField()

    class Meta:
        db_table = 'MGRCircleCycle'
        unique_together = ("cycle", "circle_member")

class MGRCirclePenalty(models.Model):
    cycle = models.ForeignKey(MGRCircleCycle, null=False, blank=False)
    circle_member = models.ForeignKey(CircleMember, null=False, blank=False)
    amount = models.IntegerField()
    fine = models.FloatField(default=0)
    date_defaulted = models.DateTimeField(auto_now=True)
    is_paid = models.BooleanField(default=False)

    class Meta:
        db_table = 'MGRCirclePenalty'

class CircleInvitation(models.Model):
    invited_by = models.ForeignKey(CircleMember, null=False, blank=False)
    is_member = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, blank=True)
    time_invited = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, default='Pending', choices=INVITE_STATUS)
    is_sent = models.BooleanField(default=False)
    priority = models.IntegerField(default=0)
    is_approved = models.BooleanField(default=True)

    class Meta:
        db_table = 'CircleInvitation'
        unique_together= ("invited_by", "phone_number")


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
    time_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'AllowedGuarantorRequest'
        unique_together = ['circle_member', 'allows_request_from']

class DeclinedCircles(models.Model):
    circle = models.ForeignKey(Circle, null=False, on_delete=models.CASCADE)
    member = models.ForeignKey(Member, null=False, on_delete=models.CASCADE)
    time_declined = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "DeclinedCircles"
        unique_together = ['circle', 'member']
