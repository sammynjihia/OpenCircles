from __future__ import absolute_import, unicode_literals
from celery import shared_task
from app_utility import loan_utils
from loan.models import GuarantorRequest



@shared_task
def unlocking_guarantors_shares(guarantors_id, shares_desc):
    instance = loan_utils.Loan()
    guarantors = GuarantorRequest.objects.filter(id=guarantors_id)
    instance.unlock_guarantors_shares(guarantors, shares_desc)
    message = "unlocked shares successfully"

    with open('celery_unlock_guarantors_shares_worker_file.txt', 'a') as post_file:
        post_file.write(str(guarantors_id))
        post_file.write("\n")

    return message