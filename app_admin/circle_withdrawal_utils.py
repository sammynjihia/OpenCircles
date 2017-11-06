from shares.models import IntraCircleShareTransaction
import datetime


class CircleWithdrawalUtils:

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








