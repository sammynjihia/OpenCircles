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
        return withdrawals['total'] if withdrawals['total'] is not None else 0

    @staticmethod
    def get_circle_locked_shares(circle):
        locked_shares = IntraCircleShareTransaction.objects.filter(shares__circle_member__circle=circle,
                                                                   transaction_type='LOCKED')\
            .aggregate(total=Sum('num_of_shares'))

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

    @staticmethod
    def get_shares_by_circle_member(circle, member):
        share_obj = Shares.objects.get(circle_member__circle=circle, circle_member__member=member)
        deposits_obj = IntraCircleShareTransaction.objects.filter(shares=share_obj, transaction_type='DEPOSIT')\
            .aggregate(total=Sum('num_of_shares'))

        withdraw_obj = IntraCircleShareTransaction.objects.filter(shares=share_obj, transaction_type='WITHDRAW') \
            .aggregate(total=Sum('num_of_shares'))

        locked_obj = IntraCircleShareTransaction.objects.filter(shares=share_obj, transaction_type='LOCKED') \
            .aggregate(total=Sum('num_of_shares'))

        unlocked_obj = IntraCircleShareTransaction.objects.filter(shares=share_obj, transaction_type='UNLOCKED') \
            .aggregate(total=Sum('num_of_shares'))

        total_deposits = deposits_obj['total'] if deposits_obj['total'] is not None else 0
        total_withdraw = withdraw_obj['total'] if withdraw_obj['total'] is not None else 0
        total_locked = locked_obj['total'] if locked_obj['total'] is not None else 0
        total_unlocked = unlocked_obj['total'] if unlocked_obj['total'] is not None else 0

        return {
            'deposit': total_deposits - total_withdraw,
            'withdraw': total_withdraw,
            'locked': total_locked - total_unlocked,
            'available_shares': (total_deposits - total_withdraw) - (total_locked - total_unlocked),
            'total_shares': ((total_deposits - total_withdraw) - (total_locked - total_unlocked)) + (total_locked - total_unlocked),
            'circle_member': share_obj.circle_member
        }

    @staticmethod
    def get_shares_trx_by_circle_member(circle_member_id):
        share_obj = Shares.objects.get(circle_member_id=circle_member_id)
        deposits_obj = IntraCircleShareTransaction.objects.filter(shares=share_obj).order_by('transaction_time')
        print(deposits_obj)
        return {
            'member': share_obj.circle_member.member,
            'transactions': deposits_obj,
            'circle': share_obj.circle_member.circle
        }

    @staticmethod
    def get_total_available_shares():
        deposits_obj = IntraCircleShareTransaction.objects.filter(transaction_type='DEPOSIT') \
            .aggregate(total=Sum('num_of_shares'))

        withdraw_obj = IntraCircleShareTransaction.objects.filter(transaction_type='WITHDRAW') \
            .aggregate(total=Sum('num_of_shares'))

        locked_obj = IntraCircleShareTransaction.objects.filter(transaction_type='LOCKED') \
            .aggregate(total=Sum('num_of_shares'))

        unlocked_obj = IntraCircleShareTransaction.objects.filter(transaction_type='UNLOCKED') \
            .aggregate(total=Sum('num_of_shares'))

        total_deposits = deposits_obj['total'] if deposits_obj['total'] is not None else 0
        total_withdraw = withdraw_obj['total'] if withdraw_obj['total'] is not None else 0
        total_locked = locked_obj['total'] if locked_obj['total'] is not None else 0
        total_unlocked = unlocked_obj['total'] if unlocked_obj['total'] is not None else 0

        return (total_deposits - total_withdraw) - (total_locked - total_unlocked)













