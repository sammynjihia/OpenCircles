from __future__ import unicode_literals
from django.db import models
from circle.models import Circle, CircleMember

class Shares(models.Model):
    circle_member = models.ForeignKey(CircleMember,related_name='shares',  null=False)
    num_of_shares = models.IntegerField(blank=False, null=False, default=0)

    class Meta:
        db_table = 'Shares'

class IntraCircleShareTransaction(models.Model):
    TRANSACTION_TYPE = [('deposit','DEPOSIT'),('transfer','TRANSFER'),('locked','LOCKED'),('unlocked','UNLOCKED')]
    shares = models.ForeignKey(Shares,related_name='shares_transaction')
    transaction_type = models.CharField(choices=TRANSACTION_TYPE,max_length=8)
    recipient = models.ForeignKey(CircleMember, null=True,related_name='recipient')
    sender = models.ForeignKey(CircleMember, null=True,related_name='sender')
    locked_loan = models.ForeignKey('loan.LoanApplication',null=True,related_name='loan')
    num_of_shares = models.IntegerField(blank=False, null=False, default=0)
    transaction_desc = models.TextField(max_length=10000, blank=False)
    transaction_time = models.DateTimeField(null=False, auto_now=True)

    class Meta:
        db_table = 'IntraCircleShareTransaction'


class LockedShares(models.Model):
    shares = models.ForeignKey(Shares,null=False,default=75)
    num_of_shares = models.IntegerField(blank=False, null=False, default=0)
    transaction_description = models.TextField(max_length=1000, blank=False)
    time_of_transaction = models.DateTimeField(null=False, auto_now=True)
    extra_info = models.TextField(max_length=10000, blank=False)

    class Meta:
        db_table = 'LockedShares'


class UnlockedShares(models.Model):
    circle_member = models.ForeignKey(CircleMember, null=False)
    num_of_shares = models.IntegerField(blank=False, null=False, default=0)
    transaction_description = models.TextField(max_length=1000, blank=False)
    time_of_transaction = models.DateTimeField(null=False, auto_now=True)
    extra_info = models.TextField(max_length=10000, blank=False)

    class Meta:
        db_table = 'UnlockedShares'
