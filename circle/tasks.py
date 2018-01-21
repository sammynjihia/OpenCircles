from __future__ import absolute_import, unicode_literals
from celery import shared_task
from app_utility import circle_utils, promotions_utils
from circle.models import CircleInvitation

@shared_task
def send_circle_invites(id_list):
    circle_invitations = CircleInvitation.objects.filter(id__in = id_list)
    instance = circle_utils.Circle()
    instance.send_circle_invitation(circle_invitations)
    message = "Saved contacts successfully"
    return message

@shared_task
def referral_programme_promotion(invite_id, amount):
    circle_invitation = CircleInvitation.objects.get(id=invite_id)
    promotion_instance = promotions_utils.Promotions()
    promotion_instance.referral_programme(circle_invitation, amount)
    message = "Disbursed referral fee successfully"
    return message
