import datetime
from loan.models import LoanApplication, LoanTariff, LoanRepayment, GuarantorRequest, LoanAmortizationSchedule
from circle.models import Circle, CircleMember
from member.models import Member
from django.db.models import Q
from django.db.models import Sum
from app_utility.sms_utils import Sms


class LoanUtils:

    @staticmethod
    def get_loan_application_by_date(search_date=None):
        if search_date is None:
            search_date = datetime.datetime.now()
        loans_applied = LoanApplication.objects.filter(
            time_of_application__range=(
                datetime.datetime.combine(search_date, datetime.time.min),
                datetime.datetime.combine(search_date, datetime.time.max)))
        return loans_applied

    @staticmethod
    def get_loan_repayment_by_date(search_date=None):
        if search_date is None:
            search_date = datetime.datetime.now()
        loans_repayment = LoanRepayment.objects.filter(
            time_of_repayment__range=(
                datetime.datetime.combine(search_date, datetime.time.min),
                datetime.datetime.combine(search_date, datetime.time.max)))
        return loans_repayment

    @staticmethod
    def get_days_pending_loans(search_date=None):
        pass

    @staticmethod
    def search_for_loan(search_val):
        sms = Sms()
        phone_number = sms.format_phone_number(search_val)
        loan_objs = LoanApplication.objects.filter(Q(loan_code=search_val)
                                                   | Q(circle_member__member__phone_number=phone_number)
                                                   | Q(circle_member__member__national_id=search_val))
        loan_objs = loan_objs.order_by('-time_of_application')
        return loan_objs

    @staticmethod
    def loan_need_guarantors(loan_code):
        try:
            return GuarantorRequest.objects.filter(loan=LoanApplication.objects.filter(loan_code=loan_code))\
                .exists()
        except:
            return False

    @staticmethod
    def get_loan_by_loan_code(loan_code):
        return LoanApplication.objects.get(loan_code=loan_code)

    @staticmethod
    def get_loan_guarantors(loan):
        return GuarantorRequest.objects.filter(loan=loan)

    @staticmethod
    def get_loan_repayment(loan):
        return LoanRepayment.objects.filter(amortization_schedule=LoanAmortizationSchedule.objects.filter(loan=loan))

    @staticmethod
    def get_total_loans_disbursed_by_circle(circle):
        total_loans = LoanApplication.objects.filter(circle_member__circle=circle, is_disbursed=True)\
            .aggregate(total=Sum('amount'))
        print(total_loans)
        return total_loans['total'] if total_loans['total'] is not None else 0

    @staticmethod
    def get_total_repaid_loans_by_circle(circle):
        total = LoanApplication.objects.filter(circle_member__circle=circle, is_disbursed=True, is_fully_repaid=True)\
            .aggregate(total=Sum('amount'))
        return total['total'] if total['total'] is not None else 0

    @staticmethod
    def get_bad_loans_by_circle(circle):
        # circle_loans = LoanApplication.objects.filter(circle_member__circle=circle, is_disbursed=True, is_fully_repaid=False)
        # non_repaid_principal = circle_loans.loan_amortization.filter(repayment_date__lt=datetime.datetime.now(), loan_repayment=None).aggregate(Sum('principal'))['principal__sum']
        # repaid_principal = circle_loans.loan_amortization.filter(~Q(loan_repayment=None)).aggregate(Sum('principal'))['principal__sum']
        # loan_amount = circle_loans.aggregate(Sum('amount'))['amount__sum']
        # return loan_amount - (repaid_principal - non_repaid_principal)
        return None






