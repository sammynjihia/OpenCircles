from __future__ import unicode_literals

from django.db import models

from circle.models import Circle, CircleMember
from member.models import Member
from shares.models import Shares, LockedShares, UnlockedShares
from deposit.models import Deposit

# Create your models here.


class LoanApplication(models.Model):
    REPAYMENT_CYCLE = (
        ('WEEK', 'Week'),
        ('MONTH', 'Month'),
        ('YEAR', 'Year')
    )

    DISBURSEMENT_CHANNELS = (
        ('MPESA', 'M-pesa'),
        ('BANK_ACCOUNT', 'Bank Account')
    )

    loan_code = models.CharField(max_length=10, blank=False, unique=True)
    circle_member = models.ForeignKey(CircleMember, null=False)
    amount = models.FloatField(null=False, blank=False, default=0.00)
    interest_rate = models.FloatField(null=False, blank=False, default=0.00)
    repayment_cycle = models.CharField(max_length=5, null=False, choices=REPAYMENT_CYCLE)
    num_of_repayment_cycles = models.IntegerField(default=1)
    require_guarantors = models.BooleanField(default=False)
    time_of_application = models.DateTimeField(null=False, auto_now=True)
    is_approved = models.BooleanField(default=False)
    time_approved = models.DateTimeField(null=True)
    is_disbursed = models.BooleanField(default=False)
    time_disbursed = models.DateTimeField(null=True)
    disbursement_channel = models.CharField(max_length=20, choices=DISBURSEMENT_CHANNELS) # Preferred mode of disbursement
    other_info = models.TextField(max_length=10000, blank=True)
    is_fully_repaid = models.BooleanField(default=False)
    time_of_last_payment = models.DateTimeField(null=True)

    class Meta:
        db_table = 'LoanApplication'


class LoanAmortizationSchedule(models.Model):
    loan_application = models.ForeignKey(LoanApplication, null=False)
    repayment_date = models.DateField(null=False)
    min_amount_payable = models.FloatField(null=False)

    class Meta:
        db_table = 'LoanAmortizationSchedule'


class LoanGuarantor(models.Model):
    loan_application = models.ForeignKey(LoanApplication, null=False)
    circle_member = models.ForeignKey(CircleMember, null=False)
    num_of_shares = models.FloatField(blank=False, null=False, default=0.00)
    time_requested = models.DateTimeField(auto_now=True)
    guaranteed = models.BooleanField(null=True, default=None)
    locked_shares = models.ForeignKey(LockedShares, null=True)
    time_processed = models.DateTimeField(null=True)

    class Meta:
        db_table = 'LoanGuarantor'


class LoanRepayment(models.Model):
    loan_application = models.ForeignKey(LoanApplication, null=False)
    amount = models.FloatField(null=False, blank=False, default=0.00)
    deposit = models.ForeignKey(Deposit, null=False)
    time_of_repayment = models.DateTimeField(null=False)
    time_created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'LoanRepayment'




