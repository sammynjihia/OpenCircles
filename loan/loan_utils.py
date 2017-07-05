import datetime
import math
from .models import Loan
from django.db.models import Count, Avg, Sum

from circle.models import Circle
from shares.models import Shares, LockedShares, UnlockedShares


class LoanApplicationProcess:

    def __int__(self, loan_data):
        self.circle_investor = loan_data['circle_investor']
        self.circle = loan_data['circle']
        self.amount = loan_data['amount']
        self.loan_cycle = loan_data['loan_cycle']
        self.application_date = loan_data['application_date']
        self.num_of_repayment_cycles = loan_data['num_of_repayment_cycles']

        self.total_amount_repayable = None
        self.available_shares = self.__get_num_of_available_shares()
        self.annual_interest = self.circle.annual_interest
        self.working_interest_rate = self.__get_working_interest_rate()

    def __applicant_has_pending_loan(self):
        """
        :return: True if there exists pending loan else False
        """
        return Loan.objects.filter(circle_investor=self.circle_investor, is_fully_repayed=False).exists()

    def __get_pending_loans(self):
        return Loan.objects.filter(circle_investor=self.circle_investor, is_fully_repayed=False)

    def __get_num_of_available_shares(self):
        gross_shares = Shares.objects.filter(circle_investor=self.circle_investor).aggregate(Sum('num_of_shares'))
        locked_shares = LockedShares.objects.filter(circle_investor=self.circle_investor).aggregate(Sum('num_of_shares'))
        unlocked_shares = UnlockedShares.objects.filter(circle_investor=self.circle_investor).aggregate(Sum('num_of_shares'))
        return gross_shares - (locked_shares - unlocked_shares)

    def __get_monthly_interest(self):
        return self.annual_interest/12
        # return math.pow(1 + self.annual_interest, 1/12) - 1

    def __get_weekly_interest(self):
        return self.annual_interest/(365/7)
        # return math.pow(1 + self.annual_interest, 1/(365/7)) - 1

    def __get_working_interest_rate(self):
        r = None
        if self.loan_cycle == 'WEEK':
            r = self.__get_weekly_interest()
        elif self.loan_cycle == 'MONTH':
            r = self.__get_monthly_interest()
        return r

    def get_amount_repaid_per_cycle(self):
        n = self.num_of_repayment_cycles
        r = self.working_interest_rate
        amount = self.amount * (r * math.pow(1 + r, n) / (math.pow(1 + r, n) - 1))
        return amount

    def __generate_loan_amortization(self):
        r = self.working_interest_rate
        amortization_table = [{
            'payment': 0,
            'amount': self.get_amount_repaid_per_cycle(),
            'interest': 0,
            'principal': '0',
            'balance': self.amount
        }]

        for i in range(1, self.num_of_repayment_cycles+1):
            a = self.get_amount_repaid_per_cycle()
            i = amortization_table[i-1]['balance'] * r
            p = a - i
            amortization_table.append({
                'payment': i,
                'amount': a,
                'interest': i,
                'principal': p,
                'balance': amortization_table[i-1]['balance'] - p
            })

        return amortization_table

    def __save_loan_application(self):
        try:
            Loan(
                circle_investor=self.circle_investor,
                amount=self.amount,
                repayment_cycle=self.loan_cycle,
                number_of_repayment_cycles=self.num_of_repayment_cycles,
                require_guarantors=self.available_shares < self.total_amount_repayable,
                time_of_application=datetime.datetime.now()
            ).save()
            return True
        except ValueError:
            return False
        except:
            return False

    def get_loan_application_message(self):
      pass


class LoanRepaymentProcess:
    pass



