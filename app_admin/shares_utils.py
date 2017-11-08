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
            transaction_type='WITHDRAW')
        return shares_withdrawal

    @staticmethod
    def get_total_shares_deposit(circle):
        deposits = IntraCircleShareTransaction.objects.filter(
            shares__circle_member__circle=circle,
            transaction_type='DEPOSIT') \
            .aggregate(total=Sum('num_of_shares'))
        return deposits['total'] if deposits['total'] is not None else 0

    @staticmethod
    def get_total_withdrawals(circle):
        withdrawals = IntraCircleShareTransaction.objects.filter(shares__circle_member__circle=circle,
                                                                 transaction_type='WITHDRAW')\
            .aggregate(total=Sum('num_of_shares'))
        return withdrawals['total']

    @staticmethod
    def get_circle_locked_shares(circle):
        locked_shares = IntraCircleShareTransaction.objects.filter(shares__circle_member__circle=circle,
                                                                   transaction_type='LOCKED')\
            .aggregate(Sum('num_of_shares'))['num_of_shares__sum']
        locked_shares = locked_shares['total'] if locked_shares['total'] is not None else 0

        unlocked_shares = IntraCircleShareTransaction.objects.filter(shares__circle_member__circle=circle,
                                                                     transaction_type='UNLOCKED')\
            .aggregate(total=Sum('num_of_shares'))

        unlocked_shares = unlocked_shares['total'] if unlocked_shares['total'] is not None else 0
        return locked_shares - unlocked_shares

    @staticmethod
    def get_circles_available_shares(circle):
        return SharesUtils.get_total_shares_deposit(circle) - (SharesUtils.get_total_withdrawals(circle)
                                                               + SharesUtils.get_circle_locked_shares(circle))

    @staticmethod
    def get_circles_total_shares(circle):
        return SharesUtils.get_total_shares_deposit(circle) - SharesUtils.get_total_withdrawals(circle)











