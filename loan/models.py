from __future__ import unicode_literals

from django.db import models

from circle.models import Circle, CircleMember
from member.models import Member
from shares.models import Shares, LockedShares, UnlockedShares

# Create your models here.


class LoanApplication(models.Model):
    loan_code = models.CharField(unique=True,max_length=20,default='LN0001')
    circle_member = models.ForeignKey(CircleMember, null=False)
    amount = models.IntegerField(null=False, blank=False, default=0)
    interest_rate = models.FloatField(null=False, blank=False, default=0.00)
    num_of_repayment_cycles = models.IntegerField(default=1)
    require_guarantors = models.BooleanField(default=False)
    time_of_application = models.DateTimeField(null=False, auto_now=True)
    is_approved = models.BooleanField(default=False)
    time_approved = models.DateTimeField(null=True)
    is_disbursed = models.BooleanField(default=False)
    time_disbursed = models.DateTimeField(null=True)
    other_info = models.TextField(max_length=10000, blank=True)
    is_fully_repaid = models.BooleanField(default=False)
    time_of_last_payment = models.DateTimeField(null=True)

    class Meta:
        db_table = 'LoanApplication'


class GuarantorRequest(models.Model):
    GUARANTOR_CHOICES = (
        (None, "Pending approval"),
        (True, "Accepted to guarantee applicant"),
        (False, "Denied to guarantee applicant")
    )
    loan_application = models.ForeignKey(LoanApplication, null=False)
    circle_member = models.ForeignKey(CircleMember, null=False)
    num_of_shares = models.IntegerField(blank=False, null=False, default=0)
    time_requested = models.DateTimeField(auto_now=True)
    has_accepted = models.NullBooleanField(choices=GUARANTOR_CHOICES, default=None)
    time_accepted = models.DateTimeField(null=True)

    class Meta:
        db_table = 'GuarantorRequest'


class LoanGuarantor(models.Model):
    loan_application = models.ForeignKey(LoanApplication, null=False)
    circle_member = models.ForeignKey(CircleMember, null=False)
    locked_shares = models.ForeignKey(LockedShares, null=False)
    time_requested = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'LoanGuarantor'


class LoanRepayment(models.Model):
    loan_application = models.ForeignKey(LoanApplication, null=False)
    amount = models.IntegerField(null=False, blank=False, default=0)
    time_of_repayment = models.DateTimeField(null=False)
    time_created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'LoanRepayment'


class LoanAmortizationSchedule(models.Model):
    loan_application = models.ForeignKey(LoanApplication, null=False)
    repayment_date = models.DateField(null=False)
    min_amount_payable = models.IntegerField(null=False)

    class Meta:
        db_table = 'LoanAmortizationSchedule'

class LoanTariff(models.Model):
    max_amount = models.IntegerField()
    min_amount = models.IntegerField()
    duration = models.IntegerField()
    monthly_interest_rate = models.FloatField()

    class Meta:
        db_table = "LoanTariff"
