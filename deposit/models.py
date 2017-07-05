from __future__ import unicode_literals

from django.db import models
from circle.models import CircleMember
# Create your models here.


class Deposit(models.Model):
    DEPOSIT_CHANNELS = (
        ('MPESA', 'M-pesa'),
        ('PESALINK', 'Pesalink')
        ('CHEQUE DEPOSIT', 'Cheque deposit'),
        ('CASH DEPOSIT', 'Cash deposit'),
        ('CARD TRANSFER', 'Card transfer'),
        ('PAYPAL', 'Paypal'),
    )

    DEPOSIT_TYPE = (
        ('LOAN_REPAYMENT', 'Loan repayment'),
        ('SHARES', 'Shares')
    )

    circle_member = models.ForeignKey(CircleMember, null=False, blank=False)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    channel = models.CharField(max_length=50, blank=False, choices=DEPOSIT_CHANNELS)
    deposit_type = models.CharField(max_length=20, blank=False, choices=DEPOSIT_TYPE)
    time_deposited = models.DateTimeField(null=False)
    other_info = models.TextField(max_length=10000, blank=True)
    time_created = models.DateField(null=False)

    class Meta:
        db_table = 'Deposit'







