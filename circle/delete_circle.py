import datetime
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from circle.models import CircleMember, Circle
from shares.models import Shares, IntraCircleShareTransaction
from wallet.models import Transactions
from app_utility import fcm_utils
from wallet.serializers import WalletTransactionsSerializer

class Delete_inactive_circles():
    def delete_circles(self):
        current_time = datetime.datetime.now().date()

        initiated_time = current_time - relativedelta(days=60)

        circles = Circle.objects.filter(~Q(time_initiated__range=[initiated_time, current_time]) & Q(is_active=False))

        # for every circle to be deleted get the circle members
        circle_members = CircleMember.objects.filter(circle__in=circles)

        # for every circle member get their shares
        member_shares = Shares.objects.filter(circle_member__in=circle_members)

        # for every shares get the transaction association
        circle_transactions = IntraCircleShareTransaction.objects.filter(shares__in=member_shares)

        # loop through the transaction list
        for circle_transaction in circle_transactions:
            trxt_desc = (
                "Circle {} has been deactivated due to inactivity. Your deposit of {} {} to the circle shall be transfered to your wallet").format(
                circle_transaction.shares.circle_member.circle.circle_name,
                circle_transaction.shares.circle_member.member.currency, circle_transaction.num_of_shares)
            time_processed = datetime.datetime.now()
            print(trxt_desc)
            circle_transaction.transaction_type = "WITHDRAW"
            circle_transaction.transaction_desc = trxt_desc
            trxt_code = "DELCIR" + circle_transaction.transaction_code
            circle_transaction.save()
            transaction = Transactions.objects.create(wallet=circle_transaction.shares.circle_member.member.wallet,
                                                      transaction_type='CREDIT', transaction_time=time_processed,
                                                      transaction_desc=trxt_desc,
                                                      transaction_amount=circle_transaction.num_of_shares,
                                                      transaction_code=trxt_code,
                                                      source="shares")
            instance = fcm_utils.Fcm()
            registration_id = circle_transaction.shares.circle_member.member.device_token
            serializer = WalletTransactionsSerializer(transaction)
            fcm_data = {"request_type": "WALLET_TO_MPESA_TRANSACTION", "transaction": serializer.data}
            instance.data_push("single", registration_id, fcm_data)

        for circle in circles:
            circle.delete()

