# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from member.models import Member

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
    transaction_time = models.DateTimeField()
    transaction_desc = models.TextField()
    transaction_amount = models.IntegerField()
    transacted_by = models.CharField(max_length=100,default="SELF")
    recipient = models.CharField(max_length=100,default="SELF")

    class Meta():
        db_table = "Transactions"
