from shares.models import IntraCircleShareTransaction, Shares
from member.models import Member
from circle.models import CircleMember
from django.db.models import Sum, Q
import datetime


class SharesUtils:

    @staticmethod
    def get_shares_withdrawal_by_date(search_date=None):
        if search_date is None:
            search_date = datetime.date.today()
        shares_withdrawal = IntraCircleShareTransaction.objects.filter(
            transaction_time__range=(
                datetime.datetime.combine(search_date, datetime.time.min),
                datetime.datetime.combine(search_date, datetime.time.max)),
            transaction_type__icontains='WITHDRAW')
        return shares_withdrawal

    @staticmethod
    def get_total_shares_deposit(circle):
        deposits = IntraCircleShareTransaction.objects.filter(
            shares=Shares.objects.filter(circle_member=CircleMember.objects.filter(circle=circle)),
            transaction_type__icontains='DEPOSIT') \
            .aggregate(Sum('num_of_shares'))['num_of_shares__sum']
        return deposits

    @staticmethod
    def get_total_withdrawals(circle):
        withdrawals = IntraCircleShareTransaction.objects.filter(
            shares=Shares.objects.filter(circle_member=CircleMember.objects.filter(circle=circle)),
            transaction_type__icontains='WITHDRAW') \
            .aggregate(Sum('num_of_shares'))['num_of_shares__sum']
        return withdrawals

    @staticmethod
    def get_circle_locked_shares(circle):
        locked_shares = IntraCircleShareTransaction.objects.filter(
            shares=Shares.objects.filter(circle_member=CircleMember.objects.filter(circle=circle)),
            transaction_type='LOCKED') \
            .aggregate(Sum('num_of_shares'))['num_of_shares__sum']
        locked_shares = locked_shares if locked_shares is not None else 0

        unlocked_shares = IntraCircleShareTransaction.objects.filter(
            shares=Shares.objects.filter(circle_member=CircleMember.objects.filter(circle=circle)),
            transaction_type='UNLOCKED') \
            .aggregate(Sum('num_of_shares'))['num_of_shares__sum']

        unlocked_shares = unlocked_shares if unlocked_shares is not None else 0
        print("Locked {} Unlocked {}".format(locked_shares, unlocked_shares))
        return locked_shares - unlocked_shares

    @staticmethod
    def get_circles_available_shares(circle):
        return SharesUtils.get_total_shares_deposit(circle) - (SharesUtils.get_total_withdrawals(circle)
                                                               + SharesUtils.get_circle_locked_shares(circle))

    @staticmethod
    def get_circles_total_shares(circle):
        return SharesUtils.get_total_shares_deposit(circle) - SharesUtils.get_total_withdrawals(circle)











