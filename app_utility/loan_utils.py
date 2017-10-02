from __future__ import division

import math
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.conf import settings

from app_utility import circle_utils

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
            data = {'repayment_date':fmt_date,'principal':format(principal,'.2f'),'interest':format(interest,'.2f'),'total_monthly_repayment':total_repayment}
            full_amortize.append(data)
            print data
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
        data = {"repayment_date":repayment_date,"starting_balance":format(starting_balance,'.2f'),"principal":format(principal,'.2f'),"interest":format(interest,'.2f'),"total_repayment":total_repayment,"ending_balance":format(ending_balance,'.2f')}
        return data
