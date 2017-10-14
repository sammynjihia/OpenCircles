from __future__ import division

import math,uuid
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import Sum

from loan.models import LoanApplication,GuarantorRequest
from shares.models import IntraCircleShareTransaction,LockedShares,UnlockedShares

from shares.serializers import SharesTransactionSerializer

from app_utility import circle_utils,fcm_utils,general_utils

class Loan():
    def validate_loan_amount(self,request,loan_amount,circle):
        circle_instance = circle_utils.Circle()
        circle_loan_limit,circle_member_loan_limit = circle_instance.get_available_circle_shares(circle),circle_instance.get_available_circle_member_shares(circle,request.user.member)
        circle_member_loan_limit = circle_member_loan_limit + settings.LOAN_LIMIT
        if loan_amount >= settings.MINIMUM_LOAN:
            if loan_amount <= settings.MAXIMUM_LOAN:
                if loan_amount <= circle_member_loan_limit:
                    return True,""
                return False,"The applied loan amount exceeds your loan limit"
            return False,"The loan amount exceeds the maximum loan tariff limit"
        return False,"The allowed minimum loan is kes %s"%(settings.MINIMUM_LOAN)

    def validate_repayment_amount(self,amount,loan_amortization):
        max_repaid_amount = loan_amortization.total_repayment + math.ceil(loan_amortization.ending_balance)
        min_repaid_amount = loan_amortization.total_repayment
        if amount >= min_repaid_amount:
            if amount <= max_repaid_amount:
                return True,""
            return False,"Amount entered exceeds the current total repayable loan amount of kes {}".format(max_repaid_amount)
        return False,"The amount entered is less than this month allowed minimun repayment amount of kes{}".format(min_repaid_amount)

    def full_amortization_schedule(self,annual_interest,balance,num_of_months,date_time_approved):
        monthly_interest = annual_interest/(12*100)
        i = monthly_interest
        n = num_of_months
        repayment = balance * ((i * math.pow(1 + i, n)) / (math.pow(1 + i, n) - 1))
        temp_date = date_time_approved
        ending_balance = balance
        full_amortize =[]
        while ending_balance > 1:
            repayment_date = temp_date + relativedelta(months=1)
            fmt_date = repayment_date.strftime('%Y-%m-%d')
            temp_date = repayment_date
            starting_balance = ending_balance
            interest = starting_balance * monthly_interest
            principal = repayment - interest
            ending_balance = max(0, starting_balance - principal)
            total_repayment = math.ceil(float(format(repayment,'.2f')))
            data = {'repayment_date':fmt_date,'principal':format(principal,'.2f'),'interest':format(interest,'.2f'),'total_monthly_repayment':total_repayment,'ending_balance':format(ending_balance,'.2f')}
            full_amortize.append(data)
        return full_amortize

    def amortization_schedule(self,annual_interest, balance, num_of_months, date_time_approved):
        monthly_interest = annual_interest/(12*100)
        i = monthly_interest
        n = num_of_months
        repayment = balance * ((i * math.pow(1 + i, n)) / (math.pow(1 + i, n) - 1))
        temp_date = date_time_approved
        repayment_date = temp_date + relativedelta(months=1)
        starting_balance = balance
        interest = starting_balance * monthly_interest
        principal = repayment - interest
        ending_balance = max(0, starting_balance - principal)
        print("Date: {0} Starting Balance: {1:.2f} principal:  {2:.2f} Interest: {3:.2f} Repayment: {4:.2f} Ending Balance: {5:.2F}".format(repayment_date, starting_balance, principal, interest, repayment,ending_balance))
        total_repayment = math.ceil(float(format(repayment,'.2f')))
        data = {"repayment_date":repayment_date,"starting_balance":float(format(starting_balance,'.2f')),"principal":float(format(principal,'.2f')),"interest":float(format(interest,'.2f')),"total_repayment":total_repayment,"ending_balance":float(format(ending_balance,'.2f'))}
        return data

    def get_total_guaranteed_amount(self,loan,shares):
        # loan = LoanApplication.objects.get(loan_code=loan_code)
        locked_shares = LockedShares.objects.filter(loan=loan).get(shares_transaction__shares=shares)
        num_of_shares = locked_shares.shares_transaction.num_of_shares
        guaranteed_amount = loan.amount - num_of_shares
        print(guaranteed_amount)
        return guaranteed_amount

    def get_remaining_guaranteed_amount(self,loan,shares):
        total_guaranteed_amount = self.get_total_guaranteed_amount(loan,shares)
        accepted_guaranteed_amount = GuarantorRequest.objects.filter(loan=loan,has_accepted=True).aggregate(total=Sum('num_of_shares'))
        guaranteed_amount = 0 if accepted_guaranteed_amount['total'] is None else accepted_guaranteed_amount['total']
        remaining_amount = total_guaranteed_amount - guaranteed_amount
        return remaining_amount

    def loan_repayment_reminder(self):
        today = datetime.now().date()
        loans = LoanApplication.objects.filter(is_fully_repaid=False,is_disbursed=True,is_approved=True)
        fcm_instance = fcm_utils.Fcm()
        for loan in loans:
            member,circle = loan.circle_member.member,loan.circle_member.circle
            days_to_send = [0,1,3,7]
            amortize_loan = loan.loan_amortization.filter()
            print(amortize_loan)
            if amortize_loan.exists():
                latest_schedule = amortize_loan.latest('id')
                diff = today - latest_schedule.repayment_date
                delta = diff.days
                if delta in days_to_send:
                    fcm_instance = fcm_utils.Fcm()
                    title = "Circle {} loan repayment".format(circle.circle_name)
                    if delta == 0:
                        message = "You loan repayment of {} {} in circle {} is due today.Kindly make the payments before end of today to avoid penalties.".format(member.currency,latest_schedule.total_repayment,circle.circle_name)
                    else:
                        message = "Remember to make your loan repayment of {} {} in circle {} before {}".format(member.currency,latest_schedule.total_repayment,circle.circle_name,latest_schedule.repayment_date)
                    registration_id = member.device_token
                    fcm_instance.notification_push("single",registration_id,title,message)

    def unlock_guarantors_shares(self, guarantors, shares_desc):
        for guarantor in guarantors:
            try:
                created_objects = []
                circle_instance = circle_utils.Circle()
                circle, member = guarantor.circle_member.circle, guarantor.circle_member.member
                shares = guarantor.circle_member.shares.get()
                shares_desc = "Shares worth {} {} have been unlocked.{}".format(member.currency, guarantor.num_of_shares, shares_desc)
                locked_shares = LockedShares.objects.filter(loan=guarantor.loan).get(shares_transaction__shares=shares)
                shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="UNLOCKED",num_of_shares=guarantor.num_of_shares,transaction_desc=shares_desc,transaction_code="ST"+uuid.uuid1().hex[:10].upper())
                created_objects.append(shares_transaction)
                unlocked_shares = UnlockedShares.objects.create(locked_shares=locked_shares, shares_transaction=shares_transaction)
                created_objects.append(unlocked_shares)
                shares_transaction_serializer = SharesTransactionSerializer(shares_transaction)
                available_shares = circle_instance.get_available_circle_member_shares(circle, member)
                loan_limit = available_shares + settings.LOAN_LIMIT
                guarantor.unlocked = True
                guarantor.save()
                instance = fcm_utils.Fcm()
                # updates available shares to other circle members
                fcm_data = {"request_type":"UNLOCK_SHARES","shares_transaction":shares_transaction_serializer.data,"loan_limit":loan_limit}
                title = "Circle {} Loan Guarantee".format(circle.circle_name)
                message = "Shares worth {} {} that were locked to guarantee {} loan have been unlocked.".format(member.currency,guarantor.num_of_shares)
                registration_id = member.device_token
                instance.data_push("single",registration_id,fcm_data)
                instance.notification_push("single",registration_id,title,message)
                fcm_available_shares = circle_instance.get_guarantor_available_shares(circle, member)
                fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES","circle_acc_number":circle.circle_acc_number,"phone_number":member.phone_number,"available_shares":fcm_available_shares}
                registration_id = instance.get_circle_members_token(circle,member)
                instance.data_push("multiple",registration_id,fcm_data)
            except Exception as e:
                print(str(e))
                general_utils.General().delete_created_objects(created_objects)

    def delete_expired_loan(self):
        today = datetime.now().date()
        loans = LoanApplication.objects.filter(is_approved=False, is_disbursed=False)
        expiry_days = [1,0]
        for loan in loans:
            loan_expiry_date = loan.time_of_application.date() + relativedelta(weeks=1)
            print(loan_expiry_date)
            print(today)
            diff = loan_expiry_date - today
            delta = diff.days
            print(delta)
            if delta in expiry_days:
                print loan.loan_code
                circle, member = loan.circle_member.circle, loan.circle_member.member
                fcm_instance = fcm_utils.Fcm()
                if delta == 1:
                    title = "Circle {} loan".format(circle.circle_name)
                    message = "Your loan of {} {} will be cancelled tomorrow.".format(member.currency,loan.amount)
                    registration_id = member.device_token
                    fcm_instance.notification_push("single",registration_id,title,message)
                else:
                    created_objects = []
                    try:
                        amount = loan.amount
                        guarantors = loan.guarantor.filter(has_accepted=True)
                        shares_desc = "The loan the shares had guaranteed has been cancelled."
                        self.unlock_guarantors_shares(guarantors,shares_desc)
                        shares = loan.circle_member.shares.get()
                        locked_shares = LockedShares.objects.filter(loan=loan).get(shares_transaction__shares=shares)
                        num_of_shares = locked_shares.shares_transaction.num_of_shares
                        shares_desc = "Shares worth {} {} have been unlocked after loan declination in circle {}".format(member.currency, num_of_shares, circle.circle_name)
                        shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares, transaction_type="UNLOCKED", num_of_shares=num_of_shares, transaction_desc=shares_desc, transaction_code="ST"+uuid.uuid1().hex[:10].upper())
                        created_objects.append(shares_transaction)
                        unlocked_shares = UnlockedShares.objects.create(locked_shares=locked_shares,shares_transaction=shares_transaction)
                        created_objects.append(unlocked_shares)
                        shares_transaction_serializer = SharesTransactionSerializer(shares_transaction)
                        instance = fcm_utils.Fcm()
                        registration_id = member.device_token
                        fcm_data = {"request_type":"DECLINE_LOAN","shares_transaction":shares_transaction_serializer.data,"loan_code":loan.loan_code}
                        fcm_instance.data_push("single",registration_id,fcm_data)
                        loan.delete()
                        title = "Circle {} loan".format(circle.circle_name)
                        message = "Your loan of {} {} in circle {} has been declined.".format(member.currency, amount,circle.circle_name)
                        fcm_instance.notification_push("single",registration_id,title,message)
                    except Exception as e:
                        print(str(e))
                        general_utils.General().delete_created_objects(created_objects)

    def calculate_total_paid_principal(self,loan):
        guaranteed = GuarantorRequest.objects.filter(loan=loan).aggregate(total=Sum('num_of_shares'))
        total_amortized = loan.loan_amortization.filter()
        interest = total_amortized.aggregate(total=Sum('interest'))
        total_paid = total_amortized.aggregate(total=Sum('loan_repayment__amount'))
        total_paid = 0 if total_paid['total'] is None else total_paid['total']
        principal = total_paid - interest['total']
        if principal >= guaranteed['total']:
            return True
        return False
