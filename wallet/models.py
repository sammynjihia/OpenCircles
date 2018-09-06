# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from member.models import Member
from circle.models import Circle
import uuid

# Create your models here.

class Wallet(models.Model):
    member = models.OneToOneField(Member, null=False, unique=True, blank=False, on_delete=models.CASCADE)
    acc_no = models.IntegerField(unique=True)

    class Meta():
        db_table = "MemberWallet"

class Transactions(models.Model):
    TRANSACTION_TYPE_CHOICE = (
        ('DEBIT', 'Debit own account'),
        ('CREDIT', 'Credit own account')
    )
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICE)
    transaction_time = models.DateTimeField(auto_now_add=True)
    transaction_desc = models.TextField()
    transaction_amount = models.FloatField()
    transacted_by = models.CharField(max_length=100, default="SELF")
    recipient = models.CharField(max_length=100, default="SELF")
    transaction_code = models.CharField(max_length=100, unique=True)
    source = models.CharField(max_length=30, null=True)

    class Meta():
        db_table = "Transactions"

class B2CTransaction_log(models.Model):
    OriginatorConversationID = models.CharField(max_length=100)
    Initiator_PhoneNumber = models.CharField(max_length=100)
    Recipient_PhoneNumber = models.CharField(max_length=100)

class B2BTransaction_log(models.Model):
    OriginatorConversationID = models.CharField(max_length=100)
    Initiator_PhoneNumber = models.CharField(max_length=100)
    Recipient_PayBillNumber = models.CharField(max_length=100)
    AccountNumber = models.CharField(max_length=100)

class RevenueStreams(models.Model):
    STREAM_TYPE_CHOICE = (
        ('LOAN INTEREST', 'revenue from loan'),
        ('SHARES WITHDRAW', 'charges of shares withdrawal'),
        ('LOAN PROCESSING', 'charges of loan processing'),
        ('CONTRIBUTION WITHDRAW', 'charges of contribution withdrawal')
    )
    stream_code = models.CharField(max_length=20)
    stream_amount = models.FloatField()
    stream_type = models.CharField(max_length=25, choices=STREAM_TYPE_CHOICE)
    time_of_transaction = models.DateTimeField()
    extra_info = models.TextField(default="", null=True)

    class Meta():
        db_table = "RevenueStreams"

class MpesaTransaction_logs(models.Model):
    OriginatorConversationID = models.CharField(max_length=100, unique=True)
    ResultCode = models.CharField(max_length=5)
    ResultDesc = models.CharField(max_length=250)
    transaction_time = models.DateTimeField(auto_now_add=True)

class AdminMpesaTransaction_logs(models.Model):
    TransactioID = models.CharField(max_length=100, unique=True)
    TransactionType = models.CharField(max_length=15)
    Response = models.TextField(max_length=1000)
    transaction_time = models.DateTimeField(auto_now_add=True)
    is_committed = models.NullBooleanField(default=None)
    is_manually_committed = models.BooleanField(default=False)

class PendingMpesaTransactions(models.Model):
    member = models.ForeignKey(Member, blank=False, null=False)
    originator_conversation_id = models.CharField(max_length=100, unique=True, blank=False)
    amount = models.FloatField()
    charges = models.FloatField(default=0)
    trx_time = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=True)
    type = models.CharField(max_length=5, default='N/A')
    purpose = models.CharField(max_length=30, default='N/A')

    class Meta:
        db_table = 'PendingMpesaTransactions'

class B2BTariff(models.Model):
    min_amount = models.IntegerField()
    max_amount = models.IntegerField()
    amount = models.IntegerField()

    class Meta:
        db_table = 'B2BTariff'

class ReferralFee(models.Model):
    member = models.ForeignKey(Member, blank=False, null=False, related_name="invited_member")
    circle = models.ForeignKey(Circle, blank=False, null=False)
    invited_by = models.ForeignKey(Member, null=True, related_name="invited_by")
    amount = models.FloatField()
    time_of_transaction = models.DateTimeField(auto_now_add=True)
    is_disbursed = models.BooleanField(default=True)
    extra_info = models.TextField()

    class Meta:
        db_table = 'ReferralFee'

class AirtimePurchaseLog(models.Model):
    member = models.ForeignKey(Member, blank=False, null=False)
    recipient = models.CharField(max_length=20)
    originator_conversation_id = models.CharField(max_length=100, unique=True, blank=False)
    time_of_transaction = models.DateTimeField(auto_now_add=True)
    is_purchased = models.BooleanField(default=False)
    extra_info = models.TextField()
    amount = models.IntegerField(default=0)
    is_committed = models.BooleanField(default=False)

    class Meta:
        db_table = 'AirtimePurchaseLog'
