from __future__ import unicode_literals

from django.db import models
from member.models import Member

# Create your models here.


class MemberTransactionSmsLog(models.Model):
    TRANSACTION_TYPE_CHOICE = (
        ('DEBIT', 'Debit own account'),
        ('CREDIT', 'Credit own account')
    )

    member = models.ForeignKey(Member, null=False, blank=False, on_delete=models.CASCADE)
    amount = models.FloatField(null=False, default=0.00)
    message_source = models.CharField(max_length=100, blank=False, default='')
    transaction_type = models.CharField(max_length=20, blank=False, default='', choices=TRANSACTION_TYPE_CHOICE)
    msg_time = models.DateTimeField(null=True)
    time_created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MemberTransactionSmsLog'


class MemberCallLog(models.Model):
    member = models.ForeignKey(Member, null=False, blank=False, on_delete=models.CASCADE)
    time_of_call = models.DateTimeField(null=False)
    duration = models.FloatField(null=False, default=0.00)
    other_info = models.TextField(max_length=10000, blank=True)

    class Meta:
        db_table = 'MemberCallLog'


class MemberCreditRating(models.Model):
    member = models.ForeignKey(Member, null=False, blank=False, on_delete=models.CASCADE)
    crb_credit_rating = models.FloatField(null=False, default=0.00)
    time_of_entry = models.DateTimeField(null=False, auto_now=True)

    class Meta:
        db_table = 'MemberCreditRating'







