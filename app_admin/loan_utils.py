import datetime
from loan.models import LoanApplication, LoanTariff, LoanRepayment, LoanGuarantor, LoanAmortizationSchedule


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






