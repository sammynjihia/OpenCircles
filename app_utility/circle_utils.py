from django.db.models import Sum
from django.conf import settings

from member.models import Member
from circle.models import Circle as CircleModel,CircleMember,CircleInvitation,DeclinedCircles
from shares.models import Shares,IntraCircleShareTransaction
from wallet.models import Transactions
from loan.models import LoanTariff, GuarantorRequest, LoanApplication
from app_utility import fcm_utils, sms_utils, wallet_utils
from django.db.models import Q
from circle.serializers import InvitedCircleSerializer
from dateutil.relativedelta import relativedelta
from wallet.serializers import WalletTransactionsSerializer
import datetime
import operator, re, datetime

class Circle():
    def get_suggested_circles(self, unjoined_circles, contacts, request, suggested_num):
        unjoined_circles = unjoined_circles.filter(circle_type="OPEN")
        circle_invites_ids = CircleInvitation.objects.filter(
                                                        phone_number=request.user.member.phone_number).values_list(
                                                                                                        "invited_by__circle",
                                                                                                        flat=True)
        invited_circles = CircleModel.objects.filter(id__in = circle_invites_ids)
        unjoined_circles = [circle for circle in unjoined_circles if circle not in invited_circles]
        suggested_circles = {}
        if len(unjoined_circles):
            suggested_num = suggested_num if(len(unjoined_circles)) > suggested_num else len(unjoined_circles)
            for circle in unjoined_circles:
                circle_count = CircleMember.objects.filter(
                                                        circle=circle,
                                                        member_id__in=Member.objects.filter(
                                                                                        phone_number__in=contacts).values_list(
                                                                                                                    "id",
                                                                                                                    flat=True)).count()
                suggested_circles[circle]=circle_count
            suggested_circles = sorted(
                                    suggested_circles.items(),
                                    key=operator.itemgetter(1),
                                    reverse=True)[0:suggested_num]
        return suggested_circles

    def check_update_circle_status(self, circle):
        if not circle.is_active:
            if CircleMember.objects.filter(circle=circle).count() >= settings.MIN_NUM_CIRCLE_MEMBER:
                circle.is_active=True
                circle.save()
                return True
            return False
        return True

    def get_invited_circles(self, request):
        circles_ids = CircleInvitation.objects.filter(phone_number=request.user.member.phone_number,
                                                      status="Pending").values_list("invited_by__circle",flat=True)
        invited_circles = CircleModel.objects.filter(id__in = circles_ids)
        return invited_circles

    def get_available_circle_shares(self, circle):
        shares = Shares.objects.filter(circle_member__circle=circle, circle_member__is_active=True)
        transactions = IntraCircleShareTransaction.objects.filter(shares__in=shares)
        deposits = transactions.filter(transaction_type="DEPOSIT").aggregate(total=Sum('num_of_shares'))
        total_deposits = 0 if deposits['total'] is None else deposits['total']
        withdraws = transactions.filter(transaction_type="WITHDRAW").aggregate(total=Sum('num_of_shares'))
        total_withdraws = 0 if withdraws['total'] is None else withdraws['total']
        transfers = transactions.filter(transaction_type="TRANSFER").aggregate(total=Sum('num_of_shares'))
        total_transfers = 0 if transfers['total'] is None else transfers['total']
        locked = transactions.filter(transaction_type="LOCKED").aggregate(total=Sum('num_of_shares'))
        total_locked = 0 if locked['total'] is None else locked['total']
        unlocked = transactions.filter(transaction_type="UNLOCKED").aggregate(total=Sum('num_of_shares'))
        total_unlocked = 0 if unlocked['total'] is None else unlocked['total']
        available_shares = (total_deposits-total_transfers-total_withdraws) - (total_locked-total_unlocked)
        return available_shares

    def get_total_circle_member_shares(self, circle, member, date):
        try:
            circle_member = CircleMember.objects.get(circle=circle, member=member)
        except CircleMember.DoesNotExist:
            return 0
        shares = circle_member.shares.get()
        if date is None:
            transactions = IntraCircleShareTransaction.objects.filter(shares=shares)
        else:
            transactions = IntraCircleShareTransaction.objects.filter(shares=shares, transaction_time__lt=date)
        deposits = transactions.filter(transaction_type="DEPOSIT").aggregate(total=Sum('num_of_shares'))
        total_deposits = 0 if deposits['total'] is None else deposits['total']
        transfers = transactions.filter(transaction_type="TRANSFER").aggregate(total=Sum('num_of_shares'))
        total_transfers = 0 if transfers['total'] is None else transfers['total']
        withdraws = transactions.filter(transaction_type="WITHDRAW").aggregate(total=Sum('num_of_shares'))
        total_withdraws = 0 if withdraws['total'] is None else withdraws['total']
        total_shares = (total_deposits-total_transfers-total_withdraws)
        return total_shares

    def get_total_circle_shares(self, circle, date, member):
        if date is None:
            transactions = IntraCircleShareTransaction.objects.filter(shares__circle_member__circle=circle)
        else:
            transactions = IntraCircleShareTransaction.objects.filter(
                                                                    ~Q(shares__circle_member__member=member)).filter(
                                                                                                                shares__circle_member__circle=circle,
                                                                                                                transaction_time__lt=date)
        deposits = transactions.filter(transaction_type="DEPOSIT").aggregate(total=Sum('num_of_shares'))
        total_deposits = 0 if deposits['total'] is None else deposits['total']
        transfers = transactions.filter(transaction_type="TRANSFER").aggregate(total=Sum('num_of_shares'))
        total_transfers = 0 if transfers['total'] is None else transfers['total']
        withdraws = transactions.filter(transaction_type="WITHDRAW").aggregate(total=Sum('num_of_shares'))
        total_withdraws = 0 if withdraws['total'] is None else withdraws['total']
        total_shares = (total_deposits-total_transfers-total_withdraws)
        return total_shares

    def get_available_unrestricted_circle_shares(self, circle, members):
        transactions = IntraCircleShareTransaction.objects.filter(
                                                                shares__circle_member__circle=circle).exclude(
                                                                                                        shares__circle_member__member__id__in=members)
        deposits = transactions.filter(transaction_type="DEPOSIT").aggregate(total=Sum('num_of_shares'))
        total_deposits = 0 if deposits['total'] is None else deposits['total']
        withdraws = transactions.filter(transaction_type="WITHDRAW").aggregate(total=Sum('num_of_shares'))
        total_withdraws = 0 if withdraws['total'] is None else withdraws['total']
        transfers = transactions.filter(transaction_type="TRANSFER").aggregate(total=Sum('num_of_shares'))
        total_transfers = 0 if transfers['total'] is None else transfers['total']
        locked = transactions.filter(transaction_type="LOCKED").aggregate(total=Sum('num_of_shares'))
        total_locked = 0 if locked['total'] is None else locked['total']
        unlocked = transactions.filter(transaction_type="UNLOCKED").aggregate(total=Sum('num_of_shares'))
        total_unlocked = 0 if unlocked['total'] is None else unlocked['total']
        available_shares = (total_deposits-total_transfers-total_withdraws) - (total_locked-total_unlocked)
        return available_shares

    def get_available_circle_member_shares(self, circle, member):
        try:
            circle_member = CircleMember.objects.get(circle=circle, member=member)
        except CircleMember.DoesNotExist:
            return 0
        shares = circle_member.shares.get()
        transactions = IntraCircleShareTransaction.objects.filter(shares=shares)
        deposits = transactions.filter(transaction_type="DEPOSIT").aggregate(total=Sum('num_of_shares'))
        total_deposits = 0 if deposits['total'] is None else deposits['total']
        transfers = transactions.filter(transaction_type="TRANSFER").aggregate(total=Sum('num_of_shares'))
        total_transfers = 0 if transfers['total'] is None else transfers['total']
        withdraws = transactions.filter(transaction_type="WITHDRAW").aggregate(total=Sum('num_of_shares'))
        total_withdraws = 0 if withdraws['total'] is None else withdraws['total']
        locked = transactions.filter(transaction_type="LOCKED").aggregate(total=Sum('num_of_shares'))
        total_locked = 0 if locked['total'] is None else locked['total']
        unlocked = transactions.filter(transaction_type="UNLOCKED").aggregate(total=Sum('num_of_shares'))
        total_unlocked = 0 if unlocked['total'] is None else unlocked['total']
        available_shares = (total_deposits-total_transfers-total_withdraws) - (total_locked-total_unlocked)
        return available_shares

    def get_guarantor_available_shares(self, circle, member):
        actual_available_shares = self.get_available_circle_member_shares(circle, member)
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        requests = GuarantorRequest.objects.filter(circle_member=circle_member, has_accepted=None)
        if requests.exists():
            amount = requests.aggregate(total=Sum('num_of_shares'))
            return actual_available_shares - amount['total']
        return actual_available_shares

    def save_loan_tariff(self, circle, loan_data):
        loan_tariffs = [LoanTariff(
                            max_amount=int(self.extract_amount(data["range"])[1]),
                            min_amount=int(self.extract_amount(data["range"])[0]),
                            num_of_months=data['months'],
                            monthly_interest_rate=data['interest'],
                            circle=circle) for data in loan_data]
        loan_tariffs = LoanTariff.objects.bulk_create(loan_tariffs)
        return loan_tariffs

    def extract_amount(self, loan_range):
        new_range = re.findall(r'\d+', loan_range)
        return new_range

    def send_circle_invitation(self, circle_invitations):
        sms_instance = sms_utils.Sms()
        for invite in circle_invitations:
            circle, member = invite.invited_by.circle, invite.invited_by.member
            if invite.is_member:
                invited_member = Member.objects.get(phone_number=invite.phone_number)
                DeclinedCircles.objects.filter(circle=circle, member=invited_member).delete()
                registration_id = invited_member.device_token
                if len(registration_id):
                    fcm_instance = fcm_utils.Fcm()
                    invited_by = "{} {}".format(member.user.first_name, member.user.last_name)
                    invited_serializer = InvitedCircleSerializer(circle, context={"invited_by":invited_by})
                    fcm_data = {"request_type":"NEW_CIRCLE_INVITATION", "circle":invited_serializer.data}
                    print(fcm_data)
                    fcm_instance.data_push("single", registration_id, fcm_data)
                else:
                    # Logged out so send sms
                    message = "{} {} has invited you to join {} on Opencircles.".format(member.user.first_name,
                                                                                        member.user.last_name,
                                                                                        circle.circle_name)
                    sms_instance.sendsms(invite.phone_number, message)
            else:
                # Not a member so send sms
                message =  "{} {} has invited you to join {} on Opencircles. " \
                           "Opencircles is a peer to peer credit and savings platform that makes you " \
                           "and your close friends, family and colleagues into investment and saving partners. " \
                           "Download the app from google play store {}".format(member.user.first_name,
                                                                               member.user.last_name,
                                                                               circle.circle_name,
                                                                               settings.APP_STORE_LINK)
                sms_instance.sendsms(invite.phone_number, message)
            invite.is_sent = True
            invite.save()

    def deactivate_circle_member(self):
        loans = LoanApplication.objects.filter(is_approved=True,
                                               is_disbursed=True,
                                               is_fully_repaid=False).exclude(loan_tariff=None)
        for loan in loans:
            member = loan.circle_member.member
            circle = loan.circle_member.circle
            loan_tariff = loan.loan_tariff
            if loan_tariff is None:
                loan_tariff = LoanTariff.objects.get(max_amount__gte=loan.amount,
                                                     min_amount__lte=loan.amount,
                                                     circle=circle)
            num_of_months = loan_tariff.num_of_months
            date_of_payment = loan.time_of_application.date() + relativedelta(months=num_of_months)
            today = datetime.datetime.now().date()
            if today > date_of_payment:
                print("defaulted loan")
                print(loan.loan_code)
                diff = datetime.datetime.now().date() - date_of_payment
                delta = diff.days
                amortize_loan = loan.loan_amortization.filter().latest('id')
                if delta == 1:
                    CircleMember.objects.filter(circle=circle, member=member).update(is_active=False)
                    title = "Circle {} account deactivation".format(circle.circle_name)

                    message = "Your account has been deactivated due to late repayment of loan {} of" \
                              " KES {} in circle {}. Kindly repay your loan to continue saving, " \
                              "borrowing and earning interests from other circle members' loans.".format(loan.loan_code,
                                                                                                         amortize_loan.total_repayment,
                                                                                                         circle.circle_name)
                    fcm_instance = fcm_utils.Fcm()
                    registration_id = member.device_token
                    if len(registration_id):
                        curr_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        fcm_data = {"request_type":"SYSTEM_WARNING_MSG",
                                    "title":title,
                                    "message":message,
                                    "time":curr_time}
                        fcm_instance.data_push("single", registration_id, fcm_data)
                        fcm_data = {"request_type":"UPDATE_CIRCLE_MEMBER_STATUS",
                                    "phone_number":member.phone_number,
                                    "circle_acc_number":circle.circle_acc_number,
                                    'is_active':False}
                        registration_ids = fcm_instance.get_circle_members_token(circle, None)
                        fcm_instance.data_push("multiple", registration_ids, fcm_data)
                    else:
                        sms_instance = sms_utils.Sms()
                        message = "Your {} account has been deactivated due to late repayment of loan {}." \
                                  "Kindly repay your loan to reactivate the account and to continue saving, " \
                                  "borrowing and earning interests from other circle members' loans.".format(
                                                                                                        circle.circle_name,
                                                                                                        loan.loan_code)
                        sms_instance.sendsms(member.phone_number, message)
                else:
                    title = "Circle {} loan repayment".format(circle.circle_name)
                    message = "Kindly repay your loan {} of KES {} in circle {} to continue saving, " \
                              "borrowing and earning interests from other " \
                              "circle members' loans.".format(loan.loan_code,
                                                              amortize_loan.total_repayment, circle.circle_name)
                    fcm_instance = fcm_utils.Fcm()
                    registration_id = member.device_token
                    if len(registration_id):
                        curr_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        fcm_data = {"request_type":"SYSTEM_WARNING_MSG", "title":title,
                                    "message":message, "time":curr_time}
                        fcm_instance.data_push("single", registration_id, fcm_data)
                    else:
                        sms_instance = sms_utils.Sms()
                        message = "Kindly repay your loan {} of KES {} in circle {} to continue saving, borrowing and earning " \
                                  "interests from other circle members' loans.".format(loan.loan_code,
                                                                                       amortize_loan.total_repayment,
                                                                                       circle.circle_name)
                        sms_instance.sendsms(member.phone_number, message)

    def delete_inactive_circles(self):
        current_time = datetime.datetime.now().date()

        initiated_time = current_time - relativedelta(days=90)

        circles = CircleModel.objects.filter(~Q(time_initiated__range=[initiated_time, current_time]) & Q(is_active=False))

        # for every circle to be deleted get the circle members
        circle_members = CircleMember.objects.filter(circle__in=circles)

        # for every circle member get their shares
        member_shares = Shares.objects.filter(circle_member__in=circle_members)

        # for every shares get the transaction association
        circle_transactions = IntraCircleShareTransaction.objects.filter(shares__in=member_shares)

        # loop through the transaction list
        for circle_transaction in circle_transactions:
            member = circle_transaction.shares.circle_member.member
            print("{} {} {}".format(member.user.first_name, member.user.last_name, member.national_id))
            wallet = member.wallet
            amount = circle_transaction.num_of_shares
            wallet_balance = wallet_utils.Wallet().calculate_wallet_balance(wallet) + amount
            trxt_desc = "Circle {} has been deactivated due to inactivity. " \
                        "Your savings of {} {} have been unlocked. " \
                        "New wallet balance is {} {}".format(circle_transaction.shares.circle_member.circle.circle_name,
                                                             member.currency,
                                                             amount, member.currency,
                                                             wallet_balance)
            time_processed = datetime.datetime.now()
            print(trxt_desc)
            circle_transaction.transaction_type = "WITHDRAW"
            circle_transaction.transaction_desc = trxt_desc
            trxt_code = "RT" + circle_transaction.transaction_code
            circle_transaction.save()
            transaction = Transactions.objects.create(wallet=circle_transaction.shares.circle_member.member.wallet,
                                                      transaction_type='CREDIT', transaction_time=time_processed,
                                                      transaction_desc=trxt_desc,
                                                      transaction_amount=amount,
                                                      transaction_code=trxt_code,
                                                      source="shares")
            instance = fcm_utils.Fcm()
            registration_id = circle_transaction.shares.circle_member.member.device_token
            serializer = WalletTransactionsSerializer(transaction)
            fcm_data = {"request_type": "WALLET_TO_MPESA_TRANSACTION", "transaction": serializer.data}
            print(fcm_data)
            instance.data_push("single", registration_id, fcm_data)

        for circle in circles:
            circle.delete()
