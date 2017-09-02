from __future__ import unicode_literals
from django.db import models
from circle.models import Circle, CircleMember
from deposit.models import Deposit


class Shares(models.Model):
    circle_member = models.ForeignKey(CircleMember,related_name='shares',  null=False)
    num_of_shares = models.FloatField(blank=False, null=False, default=0.00)

    class Meta:
        db_table = 'Shares'

class IntraCircleShareTransaction(models.Model):
    TRANSACTION_TYPE = [('deposit','DEPOSIT'),('transfer','TRANSFER')]
    shares = models.ForeignKey(Shares)
    transaction_type = models.CharField(choices=TRANSACTION_TYPE,max_length=8)
    recipient = models.ForeignKey(CircleMember, null=True,related_name='recipient')
    sender = models.ForeignKey(CircleMember, null=True,related_name='sender')
    num_of_shares = models.FloatField(blank=False, null=False, default=0.00)
    transaction_desc = models.TextField(max_length=10000, blank=False)
    transaction_time = models.DateTimeField(null=False, auto_now=True)

    class Meta:
        db_table = 'IntraCircleShareTransaction'


class LockedShares(models.Model):
    shares = models.ForeignKey(Shares,null=False,default=75)
    num_of_shares = models.FloatField(blank=False, null=False, default=0.00)
    transaction_description = models.TextField(max_length=1000, blank=False)
    time_of_transaction = models.DateTimeField(null=False, auto_now=True)
    extra_info = models.TextField(max_length=10000, blank=False)

    class Meta:
        db_table = 'LockedShares'


class UnlockedShares(models.Model):
    circle_member = models.ForeignKey(CircleMember, null=False)
    num_of_shares = models.FloatField(blank=False, null=False, default=0.00)
    transaction_description = models.TextField(max_length=1000, blank=False)
    time_of_transaction = models.DateTimeField(null=False, auto_now=True)
    extra_info = models.TextField(max_length=10000, blank=False)

    class Meta:
        db_table = 'UnlockedShares'
