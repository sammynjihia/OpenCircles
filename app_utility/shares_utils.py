from __future__ import division
from shares.models import SharesWithdrawalTariff,IntraCircleShareTransaction
from circle.models import CircleMember
from django.db.models import Min,Max
from django.conf import settings

from app_utility import circle_utils, general_utils

class Shares():
    def validate_withdrawal_amount(self,amount):
        tariff = SharesWithdrawalTariff.objects.all().aggregate(min=Min('min_amount'),max=Max('max_amount'))
        if amount >= settings.MINIMUN_WITHDRAWAL_AMOUNT:
            if amount <= tariff['max']:
                return True,""
            return False,"Amount entered exceeds the allowed maximum withdrawal shares of kes {}".format(tariff['max'])
        return False,"Amount entered is less than the allowed minimum shares withdrawal of kes {}".format(settings.MINIMUN_WITHDRAWAL_AMOUNT)

    def validate_purchased_shares(self,amount,circle,member):
        available_shares = circle_utils.Circle().get_total_circle_member_shares(circle,member,None)
        remaining_shares = settings.MAXIMUM_CIRCLE_SHARES - available_shares
        if remaining_shares >= settings.MININIMUM_CIRCLE_SHARES:
            if amount <= remaining_shares:
                return True,""
        return False,"Unable to purchase shares.The amount entered will exceed the maximum shares threshold of {} {}".format(member.currency,settings.MAXIMUM_CIRCLE_SHARES)

    def insert_circle_member_shares(self):
        circle_members = CircleMember.objects.all()
        circle_instance = circle_utils.Circle()
        for c in circle_members:
            shares = CircleMember.objects.get(circle=c.circle,member=c.member).shares.get()
            circle_member_shares = circle_instance.get_total_circle_member_shares(c.circle,c.member,None)
            total_circle_shares = circle_instance.get_total_circle_shares(c.circle,None)
            circle_shares_fraction = 0
            if total_circle_shares > 0:
                circle_shares_fraction = float(format((circle_member_shares/total_circle_shares),'.3f'))
            shares.fraction = circle_shares_fraction
            # shares.circle_name = c.circle.circle_name
            shares.save()

    def get_circle_member_shares_fraction(self,shares,time_constraint,excluded_member):
        if shares is not None:
            circle_instance = circle_utils.Circle()
            circle, member = shares.circle_member.circle, shares.circle_member.member
            circle_member_shares = circle_instance.get_total_circle_member_shares(circle,member,time_constraint)
            print("member shares")
            print(circle_member_shares)
            total_circle_shares = circle_instance.get_total_circle_shares(circle,time_constraint,excluded_member)
            print("total circle shares")
            print(total_circle_shares)
            if total_circle_shares > 0:
                circle_shares_fraction = general_utils.General().get_decimal(circle_member_shares,total_circle_shares)
            else:
                circle_shares_fraction = 0
            return circle_shares_fraction

    def get_circle_member_shares(self,shares):
        if shares is not None:
            circle_instance = circle_utils.Circle()
            circle, member = shares.circle_member.circle, shares.circle_member.member
            total_circle_shares = circle_instance.get_total_circle_shares(circle,None,None)
            print(total_circle_shares)
            circle_members = CircleMember.objects.filter(circle=circle)
            for circle_member in circle_members:
                shares = circle_member.shares.get()
                member = circle_member.member
                print(member.user.first_name)
                circle_member_shares = circle_instance.get_total_circle_member_shares(circle,member,None)
                print(circle_member_shares)
                if total_circle_shares > 0:
                    circle_shares_fraction = float(format((circle_member_shares/total_circle_shares),'.3f'))
                else:
                    circle_shares_fraction = 0
                shares.fraction = circle_shares_fraction
                shares.circle_name = circle.circle_name
                shares.save()

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
            transaction.save()
