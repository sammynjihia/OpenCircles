from __future__ import absolute_import, unicode_literals
from celery import shared_task
import app_utility as a_u
from circle.models import CircleInvitation, Circle

@shared_task
def send_circle_invites(id_list):
    circle_invitations = CircleInvitation.objects.filter(id__in = id_list)
    instance = a_u.circle_utils.Circle()
    instance.send_circle_invitation(circle_invitations)
    message = "Saved contacts successfully"
    return message

@shared_task
def referral_programme_promotion(invite_id, amount):
    circle_invitation = CircleInvitation.objects.get(id=invite_id)
    promotion_instance = a_u.promotions_utils.Promotions()
    promotion_instance.referral_programme(circle_invitation, amount)
    message = "Disbursed referral fee successfully"
    return message

@shared_task
def create_circle_cycle(circle_id, initial_time):
    circle = Circle.objects.get(id=circle_id)
    mgr_instance = a_u.mgr_utils.MerryGoRound()
    mgr_instance.create_mgr_cycle(circle, initial_time)
