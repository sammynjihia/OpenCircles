from __future__ import unicode_literals
from django.db import models

from circle.models import Circle, CircleMember

from shares.models import LockedShares

# Create your models here.
class LoanTariff(models.Model):
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE)
    max_amount = models.IntegerField()
    min_amount = models.IntegerField()
    num_of_months = models.IntegerField()
    monthly_interest_rate = models.FloatField()

    class Meta:
        db_table = "LoanTariff"

class LoanApplication(models.Model):
    loan_code = models.CharField(unique=True, max_length=20, default='LN0001')
    circle_member = models.ForeignKey(CircleMember, null=False)
    amount = models.IntegerField(null=False, blank=False, default=0)
    interest_rate = models.FloatField(null=False, blank=False, default=0.00)
    num_of_repayment_cycles = models.IntegerField(default=1)
    require_guarantors = models.BooleanField(default=False)
    time_of_application = models.DateTimeField(null=False, auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    time_approved = models.DateTimeField(null=True)
    is_disbursed = models.BooleanField(default=False)
    time_disbursed = models.DateTimeField(null=True)
    other_info = models.TextField(max_length=10000, blank=True)
    is_fully_repaid = models.BooleanField(default=False)
    time_of_last_payment = models.DateTimeField(null=True)
    loan_tariff = models.ForeignKey(LoanTariff, null=True)

    class Meta:
        db_table = 'LoanApplication'


class GuarantorRequest(models.Model):
    GUARANTOR_CHOICES = (
        (None, "Pending approval"),
        (True, "Accepted to guarantee applicant"),
        (False, "Denied to guarantee applicant")
    )
    loan = models.ForeignKey(LoanApplication, null=False,on_delete=models.CASCADE,related_name="guarantor")
    circle_member = models.ForeignKey(CircleMember, null=False)
    num_of_shares = models.IntegerField(blank=False, null=False, default=0)
    time_requested = models.DateTimeField(auto_now_add=True)
    fraction_guaranteed = models.FloatField(default=0.00)
    has_accepted = models.NullBooleanField(choices=GUARANTOR_CHOICES, default=None)
    time_accepted = models.DateTimeField(null=True)
    unlocked = models.BooleanField(default=False)
    estimated_earning = models.FloatField(default=0)

    class Meta:
        db_table = 'GuarantorRequest'
        unique_together = ('loan','circle_member')


class LoanGuarantor(models.Model):
    loan_application = models.ForeignKey(LoanApplication, null=False,on_delete=models.CASCADE)
    circle_member = models.ForeignKey(CircleMember, null=False)
    locked_shares = models.ForeignKey(LockedShares, null=False)
    time_requested = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'LoanGuarantor'

class LoanAmortizationSchedule(models.Model):
    loan = models.ForeignKey(LoanApplication, on_delete=models.CASCADE, null=False, related_name="loan_amortization")
    starting_balance = models.FloatField(null=False, default=0.0)
    principal = models.FloatField(null=False, default=0.0)
    interest = models.FloatField(null=False, default=0.0)
    total_repayment = models.FloatField(null=False, default=0.0)
    ending_balance = models.FloatField(null=False, default=0.0)
    repayment_date = models.DateField(null=False)

    class Meta:
        db_table = 'LoanAmortizationSchedule'

class LoanRepayment(models.Model):
    amortization_schedule = models.ForeignKey(LoanAmortizationSchedule, null=False,
                                              on_delete=models.CASCADE, related_name="loan_repayment")
    amount = models.IntegerField(null=False, blank=False, default=0)
    time_of_repayment = models.DateTimeField(null=False)
    time_created = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(default=4)
    class Meta:
        db_table = 'LoanRepayment'

class LoanProcessingFee(models.Model):
    min_amount = models.IntegerField()
    max_amount = models.IntegerField()
    processing_fee = models.IntegerField()

    class Meta:
        db_table = "LoanProcessingFee"
