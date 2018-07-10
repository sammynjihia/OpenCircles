from __future__ import unicode_literals
from django.db import models
from circle.models import Circle, CircleMember, MGRCircleCycle

class Shares(models.Model):
    circle_member = models.ForeignKey(CircleMember, related_name='shares', null=False)

    class Meta:
        db_table = 'Shares'

class IntraCircleShareTransaction(models.Model):
    TRANSACTION_TYPE = [('deposit','DEPOSIT'), ('transfer','TRANSFER'),
                        ('locked','LOCKED'), ('unlocked','UNLOCKED'),
                        ('withdraw','WITHDRAW')]
    shares = models.ForeignKey(Shares, related_name='shares_transaction')
    transaction_type = models.CharField(choices=TRANSACTION_TYPE, max_length=8)
    recipient = models.ForeignKey(CircleMember, null=True, related_name='recipient')
    sender = models.ForeignKey(CircleMember, null=True, related_name='sender')
    num_of_shares = models.IntegerField(blank=False, null=False, default=0)
    transaction_desc = models.TextField(max_length=10000, blank=False)
    transaction_time = models.DateTimeField(null=False, auto_now_add=True)
    transaction_code = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'IntraCircleShareTransaction'

class InitiativeCircleShareTransaction(models.Model):
    TRANSACTION_TYPE = [('deposit','DEPOSIT'),
                        ('withdraw','WITHDRAW')]
    transaction_type = models.CharField(choices=TRANSACTION_TYPE, max_length=8)
    circle_accNumber = models.CharField(max_length=100)
    transacted_by_msisdn = models.CharField(max_length=100, blank=False)
    num_of_shares = models.IntegerField(blank=False, null=False, default=0)
    transaction_desc = models.TextField(max_length=10000, blank=False)
    transaction_time = models.DateTimeField(null=False, auto_now_add=True)
    transaction_code = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'InitiativeCircleShareTransaction'

class MgrCircleTransaction(models.Model):
    TRANSACTION_TYPE = [('deposit', 'DEPOSIT'), ('withdraw', 'WITHDRAW')]
    circle_member = models.ForeignKey(CircleMember, null=False, related_name='mgr_trx')
    transaction_type = models.CharField(choices=TRANSACTION_TYPE, max_length=8)
    amount = models.IntegerField()
    transaction_code = models.CharField(max_length=20, unique=True)
    transaction_desc = models.TextField()
    transaction_time = models.DateTimeField(null=False, auto_now_add=True)
    cycle = models.ForeignKey(MGRCircleCycle, null=False, related_name='mgr_trx')

    class Meta:
        db_table = 'MgrCircleTransaction'

class LockedShares(models.Model):
    shares_transaction = models.ForeignKey(IntraCircleShareTransaction, null=False, related_name="locked")
    loan = models.ForeignKey('loan.LoanApplication', null=False, related_name="locked")

    class Meta:
        db_table = 'LockedShares'


class UnlockedShares(models.Model):
    locked_shares = models.ForeignKey(LockedShares, null=False, related_name="unlocked")
    shares_transaction = models.ForeignKey(IntraCircleShareTransaction, null=False, related_name="unlocked")

    class Meta:
        db_table = 'UnlockedShares'

class SharesWithdrawalTariff(models.Model):
    min_amount = models.IntegerField()
    max_amount = models.IntegerField()
    amount = models.IntegerField()

    class Meta:
        db_table = 'SharesWithdrawalTariff'
