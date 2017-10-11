from __future__ import division

import math
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import Sum

from loan.models import LoanApplication,GuarantorRequest
from shares.models import IntraCircleShareTransaction

from app_utility import circle_utils,fcm_utils

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
        locked_shares = IntraCircleShareTransaction.objects.get(locked_loan=loan,shares=shares)
        guaranteed_amount = loan.amount - locked_shares.num_of_shares
        return guaranteed_amount

    def get_remaining_guaranteed_amount(self,loan,shares):
        total_guaranteed_amount = self.get_total_guaranteed_amount(loan,shares)
        accepted_guaranteed_amount = GuarantorRequest.objects.filter(loan=loan,has_accepted=True).aggregate(total=Sum('num_of_shares'))
        guaranteed_amount = 0 if accepted_guaranteed_amount['total'] is None else accepted_guaranteed_amount['total']
        remaining_amount = total_guaranteed_amount - guaranteed_amount
        return remaining_amount

    def loan_repayment_reminder(self):
        today = datetime.datetime.now().date()
        loans = LoanApplication.objects.filter(is_fully_repaid=False)
        fcm_instance = fcm_utils.Fcm()
        for loan in loans:
            member,circle = loan.circle_member.member,loan.circle_member.circle
            days_to_send = [0,1,3,7]
            latest_schedule = loan.loan_amortization.filter().latest(id)
            diff = today - amortize_schedule.repayment_date.date()
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
