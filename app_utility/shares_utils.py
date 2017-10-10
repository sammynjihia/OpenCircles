from shares.models import SharesWithdrawalTariff,IntraCircleShareTransaction
from django.db.models import Min,Max

class Shares():
    def validate_withdrawal_amount(self,amount):
        tariff = SharesWithdrawalTariff.objects.all().aggregate(min=Min('min_amount'),max=Max('max_amount'))
        if amount >= tariff['min']:
            if amount <= tariff['max']:
                return True,""
            return False,"Amount entered exceeds the allowed maximum withdrawal shares of kes {}".format(tariff['max'])
        return False,"Amount entered is less than the allowed minimum shares withdrawal of kes {}".format(tariff['min'])

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
