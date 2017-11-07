# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from member.models import Member
import uuid

# Create your models here.

class Wallet(models.Model):
    member = models.OneToOneField(Member,null=False,unique=True,blank=False,on_delete=models.CASCADE)
    acc_no = models.IntegerField(unique=True)

    class Meta():
        db_table = "MemberWallet"

class Transactions(models.Model):
    TRANSACTION_TYPE_CHOICE = (
        ('DEBIT', 'Debit own account'),
        ('CREDIT', 'Credit own account')
    )
    wallet = models.ForeignKey(Wallet,on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10,choices=TRANSACTION_TYPE_CHOICE)
    transaction_time = models.DateTimeField(auto_now=True)
    transaction_desc = models.TextField()
    transaction_amount = models.FloatField()
    transacted_by = models.CharField(max_length=100,default="SELF")
    recipient = models.CharField(max_length=100,default="SELF")
    transaction_code = models.CharField(max_length=100,unique=True)
    source = models.CharField(max_length=15,null=True)

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
        ('SHARES WITHDRAW', 'charges of shares withdrawal')
    )
    stream_code = models.CharField(max_length=20)
    stream_amount = models.FloatField()
    stream_type = models.CharField(max_length=20,choices=STREAM_TYPE_CHOICE)
    time_of_transaction = models.DateTimeField()
    extra_info = models.TextField(default="")

    class Meta():
        db_table = "RevenueStreams"


class MpesaTransaction_logs(models.Model):
    OriginatorConversationID = models.CharField(max_length=100, unique=True)
    ResultCode = models.CharField(max_length=5)
    ResultDesc = models.CharField(max_length=250)


class AdminMpesaTransaction_logs(models.Model):
    TransactioID = models.CharField(max_length=100, unique=True)
    TransactionType = models.CharField(max_length=15)
    Response = models.TextField(max_length=1000)
