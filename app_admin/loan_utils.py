import datetime
from loan.models import LoanApplication, LoanTariff, LoanRepayment, GuarantorRequest, LoanAmortizationSchedule
from circle.models import Circle, CircleMember
from member.models import Member
from django.db.models import Q
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
        member_objs = Member.objects.filter(Q(Q(phone_number=sms.format_phone_number(search_val))
                                              | Q(national_id=search_val)))
        circle_member_objs = CircleMember.objects.filter(Q(Q(member=member_objs)
                                                           | Q(circle=Circle.objects.filter(circle_name__icontains=search_val))))
        loan_objs = LoanApplication.objects.filter(Q(Q(loan_code=search_val) | Q(circle_member=circle_member_objs)))
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





