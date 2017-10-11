from shares.models import SharesWithdrawalTariff,IntraCircleShareTransaction
from django.db.models import Min,Max
from django.conf import settings

from app_utility import circle_utils

class Shares():
    def validate_withdrawal_amount(self,amount):
        tariff = SharesWithdrawalTariff.objects.all().aggregate(min=Min('min_amount'),max=Max('max_amount'))
        if amount >= tariff['min']:
            if amount <= tariff['max']:
                return True,""
            return False,"Amount entered exceeds the allowed maximum withdrawal shares of kes {}".format(tariff['max'])
        return False,"Amount entered is less than the allowed minimum shares withdrawal of kes {}".format(tariff['min'])

    def validate_purchased_shares(self,amount,circle,member):
        available_shares = circle_utils.Circle().get_total_circle_member_shares(circle,member)
        print(available_shares)
        remaining_shares = settings.MAXIMUM_CIRCLE_SHARES - available_shares
        print(remaining_shares)
        if remaining_shares >= settings.MININIMUM_CIRCLE_SHARES:
            if amount <= remaining_shares:
                return True,""
        return False,"Unable to purchase shares.The amount entered will exceed the maximum shares threshold of {} {}".format(member.currency,settings.MAXIMUM_CIRCLE_SHARES)

    def save_transaction_code(self):
        transactions = IntraCircleShareTransaction.objects.all()
        for transaction in transactions:
            code = "ST{}".format(transaction.shares.circle_member.member.national_id)
            trans = IntraCircleShareTransaction.objects.filter(transaction_code__startswith = code)
            if trans.exists():
                count = trans.count()
                # value = int(latest_transaction.transaction_code[len(code):])
                new_value = count + 1
                new_value = str(new_value)
                value = new_value if len(new_value)>1 else new_value.zfill(2)
                transaction.transaction_code = code + value
            else:
                transaction.transaction_code = code + "01"
            print(transaction.transaction_code)
            transaction.save()
