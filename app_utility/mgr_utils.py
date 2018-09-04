from app_utility import fcm_utils, general_utils, wallet_utils
from app_admin import chat_utils

from django.db.models import Sum, Q

from circle.models import MGRCircleCycle, CircleMember, CircleMemberQueue, MGRCirclePenalty
from shares.models import MgrCircleTransaction, SharesWithdrawalTariff
from wallet.models import Transactions

from shares.serializers import AdminContributionsTransactionSerializer
from wallet.serializers import WalletTransactionsSerializer

import datetime


class MerryGoRound():
    def get_is_first(self, count):
        if count == 0:
            return True
        else:
            return False

    def get_next_node(self, count, max):
        next = count + 1
        if next >= max:
            next = 0
        return next

    def create_mgr_queue(self, circle):
        print('function create_mgr_queue')
        circle_members = CircleMember.objects.filter(~Q(priority=0), circle=circle, is_active=True).order_by('priority')
        print(circle_members)
        if circle_members.count() > 1:
            max = circle_members.count()
            nodes = [CircleMemberQueue(node = circle_members[count],
                                       next_node = circle_members[self.get_next_node(count, max)],
                                       is_first = self.get_is_first(count)) for count in range(0, max)]
            CircleMemberQueue.objects.bulk_create(nodes)
            return True
        return False

    def mgr_queue_remove_queue(self, circle_members):
        print('remove')
        print(circle_members)
        circle = circle_members[0].circle
        print(circle)
        circle_members_ids = circle_members.values_list('id', flat=True)
        CircleMemberQueue.objects.filter(node__id__in=circle_members_ids).delete()
        queued_circle_members = CircleMemberQueue.objects.filter(node__circle=circle).order_by('id')
        first_circle_member = queued_circle_members[0]
        if not first_circle_member.is_first:
            first_circle_member.is_first = True
            first_circle_member.save()
        last_circle_member = queued_circle_members.latest('id')
        temp_node = 0
        for cm in queued_circle_members:
            try:
                if temp_node != 0:
                    prev.next_node = cm
                    prev.save()
                    temp_node = 0
                CircleMemberQueue.objects.get(node=cm.next_node)
            except CircleMemberQueue.DoesNotExist:
                temp_node = 1
                prev = cm
                if cm == last_circle_member:
                    last_circle_member.next_node = first_circle_member.node
                    last_circle_member.save()

    def update_mgr_queue(self, circle):
        circle_member_queue = CircleMemberQueue.objects.filter(node__circle=circle)
        circle_member_queue_count = circle_member_queue.count()
        if circle_member_queue_count >= 1:
            first_circle_member = CircleMemberQueue.objects.get(node__circle=circle, is_first=True)
            last_circle_member = CircleMemberQueue.objects.get(next_node=first_circle_member.node)
            new_circle_members = CircleMember.objects.filter(~Q(priority=0), circle=circle,
                                                             is_queueing=True, is_active=True).order_by('priority')
            if new_circle_members.exists():
                print('here1')
                if circle_member_queue.count() == 1:
                    last_circle_member = first_circle_member = circle_member_queue[0]

                max = new_circle_members.count()
                print('here2')
                nodes = []
                if new_circle_members > 1:
                    nodes = [CircleMemberQueue(node=new_circle_members[count],
                                               next_node=new_circle_members[self.get_next_node(count, max)],
                                               is_first=False) for count in range(0, max)]
                nodes[max-1] = CircleMemberQueue(node=new_circle_members[max-1],
                                                 next_node=first_circle_member.node,
                                                 is_first=False)
                print(nodes[0])
                CircleMemberQueue.objects.bulk_create(nodes)
                last_circle_member.next_node = new_circle_members[0]
                last_circle_member.save()
                new_circle_members.update(is_queueing=False)
                return True
            else:
                if circle_member_queue_count == 1:
                    return False
                return True
        else:
            res = self.create_mgr_queue(circle)
            return res

    def deactivate_mgr_circle(self, circle):
        circle.is_active = False
        circle.save()
        fcm_instance = fcm_utils.Fcm()
        registration_ids = fcm_instance.get_circle_members_token(circle, None)
        fcm_data = {"request_type": "UPDATE_CIRCLE_STATUS",
                    "circle_acc_number": circle.circle_acc_number,
                    "is_active": False}
        fcm_instance.data_push("multiple", registration_ids, fcm_data)
        chat_instance = chat_utils.ChatUtils()
        message = "Circle {} has currently been deactivated. " \
                  "Kindly contact admin for further explanation.".format(circle.circle_name)
        chat_instance.send_chat_to_active_circle_members(message, circle, 1, False, None)
        message = "The circle {} has currently been deactivated due to few active members. " \
                  "Atleast two members are required for the Merry Go Round to proceed, " \
                  "to reactivate circle either invite new members" \
                  " or request defaulted members to pay their pending contributions.".format(circle.circle_name)
        chat_instance.send_chat_to_active_circle_members(message, circle, 1, True, None)


    def create_mgr_cycle(self, circle, initial_time):
        mgr_circle = circle.mgr_circle.get()
        print("mgr circle")
        print(mgr_circle)
        disbursal_date = self.calculate_disbursal_date(circle, initial_time)
        print("disbursal_date")
        print(disbursal_date)
        circle_cycle = MGRCircleCycle.objects.filter(circle_member__circle=circle).order_by('-id')
        if circle_cycle.exists():
            circle_members = CircleMemberQueue.objects.filter(node__circle=circle)
            current_cycle = circle_cycle[0]
            print("current_cycle.id")
            print(current_cycle.id)
            if circle_members.count() > 1:
                circle_member = current_cycle.circle_member.current_cmq.get().next_node
                circle_member_queue = CircleMemberQueue.objects.get(node=circle_member)
                print(current_cycle.cycle)
                cycle = current_cycle.cycle + 1 if circle_member_queue.is_first else current_cycle.cycle
                print(cycle)
                if cycle > current_cycle.cycle:
                    res = self.update_mgr_queue(circle)
                    if not res:
                        self.deactivate_mgr_circle(circle)
                        return False, 'Unable to create contribution queue.'

            else:
                res = self.update_mgr_queue(circle)
                if not res:
                    self.deactivate_mgr_circle(circle)
                    return False, 'Unable to create contribution queue.'
                cycle = current_cycle.cycle + 1
                circle_member = CircleMemberQueue.objects.get(node__circle=circle, is_first=True).node

        else:
            res = self.create_mgr_queue(circle)
            print('res')
            print(res)
            if not res:
                self.deactivate_mgr_circle(circle)
                return False, 'Unable to create contribution queue.'
            cycle = 1
            circle_member = CircleMemberQueue.objects.get(node__circle=circle, is_first=True).node

        MGRCircleCycle.objects.create(cycle=cycle, circle_member=circle_member, disbursal_date=disbursal_date)
        fcm_instance = fcm_utils.Fcm()
        message = "Your contribution of KES {} in circle {} is due before {}.".format(mgr_circle.amount,
                                                                                      circle.circle_name,
                                                                                      disbursal_date)
        print("message")
        print(message)
        registration_ids = fcm_instance.get_active_circle_members_tokens(circle, False, None)
        fcm_data = {"request_type": "UPDATE_DISBURSEMENT_DATE",
                    "circle_acc_number": circle.circle_acc_number,
                    "disbursal_date": disbursal_date.strftime("%Y-%m-%d"),
                    "message":message}
        print(fcm_data)
        fcm_instance.data_push("multiple", registration_ids,fcm_data)
        fcm_data = {"request_type": "UPDATE_CONTRIBUTION_RECIPIENT",
                    "circle_acc_number": circle.circle_acc_number,
                    "recipient": circle_member.phone_number}
        registration_ids = fcm_instance.get_active_circle_members_tokens(circle, False, True)
        fcm_instance.data_push("multiple", registration_ids, fcm_data)

        return True, ''

    def reactivate_mgr_circle(self, circle):
        circle.is_active = True
        circle.save()
        reactivated_time = datetime.date.today()
        res, msg = self.create_mgr_cycle(circle, reactivated_time)

        if res:
            message = "The circle {} has been activated. Kindly make your contribution of KES {} " \
                      "for the next round.".format(circle.circle_name, circle.mgr_circle.get().amount)
            chat_instance = chat_utils.ChatUtils()
            chat_instance.send_chat_to_active_circle_members(message, circle, 1, None, None)


    def calculate_disbursal_date(self, circle, initial_time):
        mgr_circle = circle.mgr_circle.get()
        if mgr_circle.schedule.lower() == "monthly":
            disbursal_date = initial_time + datetime.timedelta(days=30)

        else:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            initial_day = initial_time.weekday()
            scheduled_day = days.index(mgr_circle.day)
            delta = 7 - (initial_day - scheduled_day)
            disbursal_date = initial_time + datetime.timedelta(days=delta)

        return disbursal_date

    def commit_disbursals(self, transaction_amount, circle_cycle):
        general_instance = general_utils.General()
        wallet_instance = wallet_utils.Wallet()
        recipient = circle_cycle.circle_member
        circle = recipient.circle
        #to_do:create withdrawal tariff for MGR
        transaction_cost = SharesWithdrawalTariff.objects.get(max_amount__gte=transaction_amount,
                                                              min_amount__lte=transaction_amount).amount
        actual_amount = transaction_amount - transaction_cost
        transaction_code = general_instance.generate_unique_identifier('CTW')
        transaction_desc = "{} confirmed. KES {} has been sent to {}.".format(transaction_code,
                                                                              transaction_amount,
                                                                              recipient.member.phone_number)
        general_instance = general_utils.General()
        created_objects = []
        try:
            total_contributions = self.get_mgr_circle_total_contributions(circle)
            if total_contributions >= transaction_amount:
                contributions_trx = MgrCircleTransaction.objects.create(transaction_code=transaction_code,
                                                                        amount=transaction_amount,
                                                                        transaction_type="WITHDRAW",
                                                                        transaction_time=datetime.datetime.now(),
                                                                        transaction_desc=transaction_desc,
                                                                        circle_member=recipient,
                                                                        cycle=circle_cycle)
            else:
                return
            created_objects.append(contributions_trx)
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
                                                             transaction_type="CREDIT",
                                                             transaction_time=datetime.datetime.now(),
                                                             transaction_desc=wallet_desc,
                                                             source="wallet",
                                                             transacted_by=circle.circle_acc_number
                                                             )
            created_objects.append(wallet_transaction)
            wallet_serializer = WalletTransactionsSerializer(wallet_transaction)
            contribution_serializer = AdminContributionsTransactionSerializer(contributions_trx)
            circle_cycle.is_complete = True
            circle_cycle.save()
            self.penalize_circle_members(circle_cycle, created_objects)
            data = {"wallet_transaction": wallet_serializer.data, "contribution": contribution_serializer.data}
            return data
        except Exception as e:
            print(str(e))
            general_instance.delete_created_objects(created_objects)
            circle_cycle.is_complete = False
            circle_cycle.save()
            return ''

    def disburse_contributions(self):
        #to_do:celerify function
        circles_cycles = MGRCircleCycle.objects.filter(is_complete=False, disbursal_date__lte=datetime.date.today())
        print(circles_cycles.count())
        for circle_cycle in circles_cycles:
            delta = datetime.date.today() - circle_cycle.disbursal_date
            days = delta.days
            print(days)
            if days == 0:
                circle = circle_cycle.circle_member.circle
                trx = MgrCircleTransaction.objects.filter(circle_member__circle=circle,
                                                          cycle=circle_cycle).aggregate(total_amount=Sum('amount'))
                total_contributed_amount = 0 if trx['total_amount'] is None else trx['total_amount']
                print("total_contributed_amount")
                print(total_contributed_amount)
                total_circle_members = CircleMember.objects.filter(~Q(priority=0),
                                                                   circle=circle,
                                                                   is_active=True,
                                                                   is_queueing=False).count()
                print(total_circle_members)
                print(circle.mgr_circle.get().amount)
                circle_amount = circle.mgr_circle.get().amount
                expected_total_amount = total_circle_members * circle_amount
                member = circle_cycle.circle_member.member
                if total_contributed_amount == expected_total_amount:
                    try:
                        data = self.commit_disbursals(total_contributed_amount, circle_cycle)
                        if not data:
                            return
                        fcm_instance = fcm_utils.Fcm()
                        registration_id = member.device_token
                        fcm_data = {"request_type": "CREDIT_WALLET",
                                    "wallet_transaction": data['wallet_transaction']}
                        fcm_instance.data_push("single", registration_id, fcm_data)
                        registration_ids = fcm_instance.get_circle_admins_tokens(circle)
                        fcm_data = {"request_type": "UPDATE_MGR_CONTRIBUTION",
                                    "contribution": data['contribution']
                                    }
                        fcm_instance.data_push("multiple", registration_ids, fcm_data)

                    except Exception as e:
                        print(str(e))
                        return
                else:
                    chat_instance = chat_utils.ChatUtils()
                    message = "Unable to automatically disburse KES {} to {} {} in circle {}" \
                              "due to failure of members to contribute.".format(expected_total_amount,
                                                                                member.user.first_name,
                                                                                member.user.last_name,
                                                                                circle.circle_name)
                    chat_instance.send_chat_to_active_circle_members(message, circle, 1, True, None)

    def get_circle_member_penalty_amount(self, circle_member):
        penalties = MGRCirclePenalty.objects.filter(circle_member=circle_member, is_paid=False)
        penalty_amount = 0
        if penalties.exists():
            penalties = penalties.aggregate(total_amount=Sum('amount'),
                                            total_fine=Sum('fine'))
            total_amount = 0 if penalties['total_amount'] is None else penalties['total_amount']
            total_fine = 0 if penalties['total_fine'] is None else penalties['total_fine']
            penalty_amount = total_amount + total_fine
        return penalty_amount

    def reinstate_defaulted_circle_member(self, circle_member, join_cycle):
        circle_member.is_active = True
        circle_member.save()
        circle = circle_member.circle
        circle_members = CircleMember.objects.filter(~Q(priority=0),
                                                    circle=circle,
                                                    is_queueing=False,
                                                    is_active=True).order_by('-priority')
        if circle_members.exists():
            priority= circle_members[0].priority

        else:
            circle_members = CircleMember.objects.filter(~Q(priority=0),
                                                         circle=circle,
                                                         is_active=True).order_by('-priority')
            if circle_members.exists():
                priority = circle_members[0].priority
            else:
                priority = 0

        circle_member.priority = priority + 1
        if join_cycle:
            circle_member.is_queueing = False
            circle_member.save()
            res = self.update_mgr_queue(circle)

        else:
            circle_member.is_queueing = True
            circle_member.save()
            if not circle.is_active:
                circle_members_count = CircleMember.objects.filter(circle=circle, is_active=True).count()
                if circle_members_count > 1:
                    self.reactivate_mgr_circle(circle)
        return True

    def cycle_join_status(self, circle_member):
        circle = circle_member.circle
        current_cycle = MGRCircleCycle.objects.filter(circle_member__circle=circle).latest('id')
        cycle = MGRCirclePenalty.objects.filter(circle_member=circle_member, is_paid=False).latest('id').cycle
        data = {'has_received':False, 'join_cycle':False}
        if current_cycle.cycle == cycle.cycle:
            try:
                MgrCircleTransaction.objects.get(cycle=current_cycle, circle_member=circle_member, transaction_type="WITHDRAW")
                data['has_received'] = True
            except MgrCircleTransaction.DoesNotExist:
                if circle.is_active:
                    data['join_cycle'] = True
        return data

    def validate_circle_member_contribution(self, circle_member):
        circle = circle_member.circle
        data = {}
        if circle_member.is_active:
            if circle_member.is_queueing:
                data = {"status": 0,
                        "message": "Unable to process transaction. New round has not yet begun."}
                return False, data

            try:
                circle_cycle = MGRCircleCycle.objects.get(circle_member__circle=circle, is_complete=False)
                try:
                    MgrCircleTransaction.objects.get(circle_member=circle_member, cycle=circle_cycle,
                                                     transaction_type="DEPOSIT")
                    data = {"status": 0,
                            "message": "Unable to process transaction. You have already made your contributions "
                                       "for the current round."}
                    return False, data
                except MgrCircleTransaction.DoesNotExist:
                    return True, data

            except MGRCircleCycle.DoesNotExist:
                data = {"status": 0, "message": "Unable to process transaction. The next contribution "
                                                "cycle for the circle {} has not commenced.".format(circle.circle_name)}
                return False, data
        data = {"status": 0, "message": "Unable to process transaction. Your circle account is currently deactivated."}
        return False, data

    def process_paid_penalties(self, circle_member):
        created_objects = []
        general_instance = general_utils.General()
        try:
            penalties = MGRCirclePenalty.objects.filter(circle_member=circle_member)
            member, circle = circle_member.member, circle_member.circle
            for penalty in penalties:
                cycle = penalty.cycle
                total_amount = penalty.amount + penalty.fine
                general_instance = general_utils.General()
                transaction_code = general_instance.generate_unique_identifier('CTD')
                transaction_desc = "{} confirmed. You have contributed {} {}.".format(
                    transaction_code,
                    member.currency,
                    total_amount)
                depo_trx = MgrCircleTransaction.objects.create(circle_member=circle_member,
                                                               transaction_type="DEPOSIT",
                                                               amount=total_amount,
                                                               transaction_code=transaction_code,
                                                               transaction_desc=transaction_desc,
                                                               transaction_time=datetime.datetime.now(),
                                                               cycle=cycle)
                created_objects.append(depo_trx)
                #to_do:update contribution on admin side with fcm
                recipient_circle_member = cycle.circle_member
                transaction_code = transaction_code.replace('CTD', 'CTW')
                transaction_desc = "{} confirmed. {} {} sent to {}.".format(transaction_code,
                                                                            member.currency,
                                                                            total_amount,
                                                                            recipient_circle_member.member.phone_number)
                transaction_cost = SharesWithdrawalTariff.objects.get(max_amount__gte=total_amount,
                                                                      min_amount__lte=total_amount).amount
                actual_amount = total_amount - transaction_cost
                total_contributions = self.get_mgr_circle_total_contributions(circle)
                if total_contributions >= total_amount:
                    withdraw_depo = MgrCircleTransaction.objects.create(circle_member=cycle.circle_member,
                                                                        transaction_type="WITHDRAW",
                                                                        amount=total_amount,
                                                                        transaction_code=transaction_code,
                                                                        transaction_desc=transaction_desc,
                                                                        transaction_time=datetime.datetime.now(),
                                                                        cycle=cycle)
                else:
                    return
                created_objects.append(withdraw_depo)
                #to_do:update contribution on admin side with fcm
                wallet = recipient_circle_member.member.wallet
                wallet_instance = wallet_utils.Wallet()
                transaction_code = transaction_code.replace('CTW', 'WTC')
                wallet_balance = wallet_instance.calculate_wallet_balance(wallet) + total_amount
                #to_do:edit below wallet trx
                wallet_desc = "{} confirmed. You have received defaulted contribution of {} {} from circle {}. " \
                              "Transaction cost {} {}. New wallet balance is {} {}.".format(transaction_code,
                                                                                            member.currency,
                                                                                            actual_amount,
                                                                                            member.currency,
                                                                                            transaction_cost,
                                                                                            circle.circle_name,
                                                                                            member.currency,
                                                                                            wallet_balance)
                #to_do:apply contribution tariff
                wallet_transaction = Transactions.objects.create(wallet=wallet,
                                                                 transaction_type="CREDIT",
                                                                 transaction_time=datetime.datetime.now(),
                                                                 transaction_desc=wallet_desc,
                                                                 transaction_amount=actual_amount,
                                                                 transacted_by=circle.circle_acc_number,
                                                                 transaction_code=transaction_code,
                                                                 source="contribution")
                created_objects.append(wallet_transaction)
                wallet_transaction_serializer = WalletTransactionsSerializer(wallet_transaction)
                penalty.is_paid = True
                penalty.save()
                if not cycle.is_complete:
                    cycle.is_complete = True
                    cycle.save()
                fcm_data = {"request_type":"CREDIT_WALLET",
                            "wallet_transaction":wallet_transaction_serializer.data}
                fcm_instance = fcm_utils.Fcm()
                registration_id = recipient_circle_member.member.device_token
                fcm_instance.data_push("single", registration_id, fcm_data)

        except Exception as e:
            print(str(e))
            general_instance.delete_created_objects(created_objects)
    def deactivate_defaulters(self, defaulters):
        defaulters.update(is_active=False, priority=0)

    def penalize_circle_members(self, circle_cycle, created_objects):
        circle_member = circle_cycle.circle_member
        circle = circle_member.circle
        print("hapa2")
        contributors_ids = MgrCircleTransaction.objects.filter(circle_member__circle=circle,
                                                               cycle=circle_cycle,
                                                               transaction_type="DEPOSIT").values_list('circle_member__id',
                                                                                                       flat=True)
        print(contributors_ids)
        #to_do:NB if the receiving contributor_id in defaulted members he/she is removed

        print("hapa3")
        if circle_member.id not in contributors_ids:
            contributors_ids = list(contributors_ids)
            contributors_ids.append(circle_member.id)

        print(contributors_ids)
        defaulters = CircleMember.objects.filter(~Q(priority=0),
                                                 ~Q(id__in=contributors_ids),
                                                 is_active=True,
                                                 is_queueing=False,
                                                 circle=circle)
        contributed_to = MgrCircleTransaction.objects.filter(circle_member=circle_member,
                                                             cycle__cycle=circle_cycle.cycle,
                                                             transaction_type="DEPOSIT").exclude(cycle__circle_member=circle_member).values_list('cycle__circle_member__id',
                                                                                                     flat=True)
        prev_defaulters = CircleMember.objects.filter(id__in=contributed_to, is_active=False, priority=0)
        print("prev_defaulters")
        print(prev_defaulters.values_list('id', flat=True))
        print("defaulters")
        print(defaulters)
        total_defaulters = defaulters | prev_defaulters
        print('total_defaulters.count()')
        print(total_defaulters.count())
        if total_defaulters.count() > 0:
            amount = circle.mgr_circle.get().amount
            penalty_query = [MGRCirclePenalty(cycle=circle_cycle, circle_member=defaulter,
                                              amount=amount,
                                              fine=(circle.mgr_circle.get().fine/100)*amount) for defaulter in total_defaulters]
            penalities = MGRCirclePenalty.objects.bulk_create(penalty_query)
            created_objects.append(penalities)
            print("penalities")
            print(penalities)
            if defaulters.exists():
                self.mgr_queue_remove_queue(defaulters)
                #to_do:edit msg
                chat_instance = chat_utils.ChatUtils()
                message = "Your circle {} account has been deactivated due to delayed contribution.".format(circle.circle_name)
                registration_ids = list(defaulters.values_list('member__device_token', flat=True))
                print("registration_ids")
                print(registration_ids)
                chat_instance.send_chat_to_active_circle_members(message, circle, 1, None, registration_ids)
                self.deactivate_defaulters(defaulters)
        self.create_mgr_cycle(circle, datetime.date.today())

    def get_mgr_circle_total_contributions(self, circle):
        transactions = MgrCircleTransaction.objects.filter(circle_member__circle=circle)
        total_deposits = transactions.filter(transaction_type="DEPOSIT").aggregate(amount=Sum('amount'))
        total_deposits = total_deposits['amount'] if total_deposits['amount'] is not None else 0
        total_withdraws = transactions.filter(transaction_type="WITHDRAW").aggregate(amount=Sum('amount'))
        total_withdraws = total_withdraws['amount'] if total_withdraws['amount'] is not None else 0
        total_amount = total_deposits - total_withdraws
        return total_amount









