from __future__ import unicode_literals
from django.db import models
from circle.models import Circle, CircleMember
from deposit.models import Deposit


class IntraCircleShareTransfer(models.Model):
    transfer_from = models.ForeignKey(CircleMember, null=False, related_name='transfer_from')
    transfer_to = models.ForeignKey(CircleMember, null=False, related_name='transfer_to')
    num_of_shares = models.FloatField(blank=False, null=False, default=0.00)
    time_of_transaction = models.DateTimeField(null=False, auto_now=True)
    extra_info = models.TextField(max_length=10000, blank=False)

    class Meta:
        db_table = 'IntraCircleShareTransfer'


class Shares(models.Model):
    circle_member = models.ForeignKey(CircleMember, null=False)
    deposit = models.ForeignKey(Deposit, null=True)
    intra_share_transfer = models.ForeignKey(IntraCircleShareTransfer, null=True)
    num_of_shares = models.FloatField(blank=False, null=False, default=0.00)
    time_acquired = models.DateTimeField(null=True)
    time_created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Shares'


class LockedShares(models.Model):
    circle_member = models.ForeignKey(CircleMember, null=False)
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


