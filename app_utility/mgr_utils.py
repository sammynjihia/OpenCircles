from app_utility import fcm_utils, general_utils, wallet_utils

from django.db.models import Sum

from circle.models import MGRCircleCycle, CircleMember
from shares.models import MgrCircleTransaction, SharesWithdrawalTariff
from wallet.models import Transactions

from shares.serializers import ContributionsTransactionSerializer
from wallet.serializers import WalletTransactionsSerializer

import datetime, calendar


class MerryGoRound():
    def create_mgr_cycle(self, circle, initial_time):
        print(circle)
        extra_circle = circle.extra_circle.get()
        disbursal_date = self.calculate_disbursal_data(circle, initial_time)
        circle_cycle = MGRCircleCycle.objects.filter(circle_member__circle=circle)
        if circle_cycle.exists():
            circle_cycle = circle_cycle.order_by('-id')[0]
            # cycle = circle_cycle.cycle
            # cycle_string = str(circle)
            # cycle_list = cycle_string.split('.')
            # cycle_num, priority = int(cycle_list[0]), int(cycle_list[1])
            priority = circle_cycle.circle_member.priority + 1
            try:
                CircleMember.objects.get(circle=circle, priority=priority)
            except CircleMember.DoesNotExist:
                priority = 1
            cycle = circle_cycle.cycle + 1
        else:
            cycle = 1.1
            priority = 1
        circle_member = CircleMember.objects.get(circle=circle, priority=priority)
        MGRCircleCycle.objects.create(cycle=cycle, circle_member=circle_member, disbursal_date=disbursal_date)
        fcm_instance = fcm_utils.Fcm()
        curr_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = "Circle {} Contribution".format(circle.circle_name)
        message = "Your contribution of KES {} is due before {}.".format(extra_circle.amount, disbursal_date)
        fcm_data = {"request_type": "SYSTEM_WARNING_MSG",
                    "title": title,
                    "message": message,
                    "time": curr_time}
        registration_ids = fcm_instance.get_circle_members_token(circle, None)
        fcm_instance.data_push("multiple", registration_ids, fcm_data)

    def calculate_disbursal_data(self, circle, initial_time):
        extra_circle = circle.extra_circle.get()
        if extra_circle.schedule.lower() == "monthly":
            disbursal_date = initial_time + datetime.timedelta(days=30)

        else:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            initial_day = initial_time.weekday()
            scheduled_day = days.index(extra_circle.day)
            delta = 7 - (initial_day - scheduled_day)
            disbursal_date = initial_time + datetime.timedelta(days=delta)

        return disbursal_date

    def disburse_contributions(self):
        circles_cycles = MGRCircleCycle.objects.filter(is_complete=False, disbursal_date__lte=datetime.datetime.now().date)
        for circle_cycle in circles_cycles:
            delta = datetime.datetime.now().date - circle_cycle.disbursal_date
            days = delta.days
            if days == 0:
                circle = circle_cycle.circle_member.circle
                trx = MgrCircleTransaction.objects.filter(circle_member__circle=circle,
                                                          cycle=circle_cycle).aggregate(total_amount=Sum('amount'))
                total_contributed_amount = 0 if trx['total_amount'] is None else trx['total_amount']
                total_circle_members = CircleMember.objects.filter(circle=circle, is_active=True).count()
                expected_total_amount = total_circle_members * circle_cycle.amount
                member = circle_cycle.circle_member.member
                if total_contributed_amount == expected_total_amount:
                    try:
                        data = self.commit_disbursals(total_contributed_amount, circle)

                    except Exception as e:
                        return
                else:
                    title = "Circle {} Contribution Disbursal".format(circle.circle_name)
                    message = "Unable to automatically disburse KES {} to {} {} " \
                              "due to failure of some members to contribute.".format(expected_total_amount,
                                                                                     member.user.first_name,
                                                                                     member.user.last_name)
                    curr_time = datetime.datetime.now()
                    fcm_data = {"request_type": "SYSTEM_WARNING_MSG",
                                "title": title,
                                "message": message,
                                "time": curr_time}
                    fcm_instance = fcm_utils.Fcm()
                    registration_ids = fcm_instance.get_circle_members_token(circle, None)
                    fcm_instance.data_push("multiple", registration_ids, fcm_data)

    def commit_disbursals(self, transaction_amount, circle):
        general_instance = general_utils.General()
        wallet_instance = wallet_utils.Wallet()
        circle_cycle = MGRCircleCycle.objects.filter(circle_member__circle=circle).order_by('-id')[0]
        recipient = circle.circle_cycle.circle_member
        transaction_cost = SharesWithdrawalTariff.objects.get(max_amount__gte=transaction_amount,
                                                              min_amount__lte=transaction_amount).amount
        actual_amount = transaction_amount - transaction_cost
        transaction_code = general_instance.generate_unique_identifier('CTW')
        transaction_desc = "{} confirmed. KES {} has been sent to {}.".format(transaction_code,
                                                                              transaction_amount,
                                                                              circle_cycle.circle_member.member.phone_number)
        contributions_trx = MgrCircleTransaction.objects.create(transaction_code=transaction_code,
                                                                amount=transaction_amount,
                                                                transaction_type="WITHDRAW",
                                                                transaction_time=datetime.datetime.now(),
                                                                transaction_desc=transaction_desc,
                                                                circle_member=recipient)
        transaction_code = transaction_code.replace('CTW', 'WTC')
        wallet_balance = wallet_instance.calculate_wallet_balance(recipient.member.wallet) + actual_amount
        wallet_desc = "{} confirmed. You have received {} {} from circle {}. Transaction cost {} {}." \
                      "New wallet balance is {} {}".format(transaction_code,
                                                           recipient.member.currency,
                                                           actual_amount,
                                                           circle.circle_name,
                                                           recipient.member.currency,
                                                           transaction_cost,
                                                           recipient.member.currency,
                                                           wallet_balance)
        wallet_transaction = Transactions.objects.create(wallet=recipient.member.wallet,
                                                         transaction_code=transaction_code,
                                                         transaction_amount=actual_amount,
                                                         transaction_type="DEBIT",
                                                         transaction_time=datetime.datetime.now(),
                                                         transaction_desc=wallet_desc,
                                                         source="wallet",
                                                         sender=circle.circle_acc_number
                                                         )
        wallet_serializer = WalletTransactionsSerializer(wallet_transaction)
        contribution_serializer = ContributionsTransactionSerializer(contributions_trx)
        circle_cycle.is_complete = True
        circle_cycle.save()
        priority = circle_cycle.circle_member.priority + 1
        try:
            next_circle_member = CircleMember.objects.get(priority=priority, circle=circle, is_active=True)
        except CircleMember.DoesNotExist:
            priority = 1
            next_circle_member = CircleMember.objects.get(priority=priority, circle=circle)
        cycle_num = circle_cycle.cycle + 1
        disbursal_date = self.calculate_disbursal_data(circle, datetime.datetime.now().date())
        MGRCircleCycle.objects.create(circle_member=next_circle_member,
                                   disbursal_date=disbursal_date,
                                   cycle=cycle_num)
        data = {"wallet_transaction": wallet_serializer.data, "contribution": contribution_serializer.data}
        fcm_instance = fcm_utils.Fcm()
        fcm_data = {"request_type": "UPDATE_DISBURSEMENT_DATE",
                    "circle_acc_number": circle.circle_acc_number,
                    "disbursal_date": disbursal_date}
        registration_ids = fcm_instance.get_circle_members_token(circle, None)
        fcm_instance.data_push("multiple", registration_ids, fcm_data)
        title = "Circle {} Contribution".format(circle.circle_name)
        extra_circle = circle.extra_circle.get()
        message = "Your contribution of KES {} is due before {}.".format(extra_circle.amount,
                                                                         disbursal_date)
        curr_time = datetime.datetime.now()
        fcm_data = {"request_type": "SYSTEM_WARNING_MSG",
                    "title": title,
                    "message": message,
                    "time": curr_time}
        fcm_instance.data_push("multiple", registration_ids, fcm_data)
        return data

