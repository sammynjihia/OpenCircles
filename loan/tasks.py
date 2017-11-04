from __future__ import absolute_import, unicode_literals
from celery import shared_task
from app_utility import loan_utils
from loan.models import GuarantorRequest
from circle.models import Circle
from member.models import Member
from loan.models import LoanApplication



@shared_task
def unlocking_guarantors_shares(guarantors_id, shares_desc):
    instance = loan_utils.Loan()
    guarantors = GuarantorRequest.objects.filter(id__in=guarantors_id)
    instance.unlock_guarantors_shares(guarantors, shares_desc)
    message = "unlocked shares successfully"
    with open('celery_unlock_guarantors_shares_worker_file.txt', 'a') as post_file:
        post_file.write(str(guarantors_id))
        post_file.write("\n")
    return message

@shared_task
def updating_loan_limit(circle_id, member_id):
    instance = loan_utils.Loan()
    circle = Circle.objects.get(id=circle_id)
    member = Member.objects.get(id=member_id)
    instance.update_loan_limit(circle, member)
    log_message = "Updated loan limit successfully"
    with open('celery_updating_loan_limit_worker_file.txt', 'a') as post_file:
        post_file.write(str(circle_id))
        post_file.write("\n")
        post_file.write(str(member_id))
        post_file.write("\n")
    return log_message

@shared_task
def sending_guarantee_requests(guarantors_id, member_id):
    guarantors = GuarantorRequest.objects.filter(id__in=guarantors_id)
    member = Member.objects.get(id=member_id)
    instance = loan_utils.Loan()
    instance.send_guarantee_requests(guarantors, member)
    log_message = "Sent guarantee request successfully"
    with open('celery_updating_loan_limit_worker_file.txt', 'a') as post_file:
        post_file.write(str(guarantors_id))
        post_file.write("\n")
        post_file.write(str(member_id))
        post_file.write("\n")
    return log_message

@shared_task
def task_share_loan_interest(loan_id):
    loan = LoanApplication.objects.get(id=loan_id)
    with open('celery_share_loan_interest_loan_worker_file.txt', 'a') as post_file:
        post_file.write(str(loan_id))
        post_file.write("\n")
        post_file.write(str(type(loan_id)))
    instance = loan_utils.Loan()
    instance.share_loan_interest(loan)
    log_message = "Loan interest successful"
    with open('celery_share_loan_interest_worker_file.txt', 'a') as post_file:
        post_file.write(str(loan_id))
        post_file.write("\n")
    return log_message
