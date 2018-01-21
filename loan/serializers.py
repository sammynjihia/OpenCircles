from rest_framework import serializers
from loan.models import LoanApplication, LoanTariff, LoanRepayment, LoanAmortizationSchedule, GuarantorRequest, LoanProcessingFee
from app_utility import loan_utils


class LoanApplicationSerializer(serializers.Serializer):
    loan_amount = serializers.IntegerField()
    pin = serializers.CharField()
    guarantors = serializers.ListField()
    circle_acc_number = serializers.CharField()

    class Meta:
        fields = ['loan_amount', 'pin', 'guarantors', 'circle_acc_number']

class LoanRepaySerializer(serializers.Serializer):
    amount = serializers.FloatField()
    pin = serializers.CharField()
    loan_code = serializers.CharField()

    class Meta:
        fields = ['amount', 'pin', 'loan_code']

class LoansSerializer(serializers.ModelSerializer):
    """
    Serializer for loan listing endpoint
    """
    time_of_application = serializers.SerializerMethodField()
    time_approved = serializers.SerializerMethodField()
    time_disbursed = serializers.SerializerMethodField()
    time_of_last_payment = serializers.SerializerMethodField()
    locked_shares = serializers.SerializerMethodField()
    class Meta:
        model = LoanApplication
        fields = ['amount', 'loan_code', 'locked_shares', 'num_of_repayment_cycles', 'time_of_application',
                  'is_approved', 'time_approved', 'is_disbursed', 'time_disbursed', 'is_fully_repaid', 'time_of_last_payment']

    def get_time_of_application(self, loan):
        return loan.time_of_application.strftime("%Y-%m-%d %H:%M:%S")

    def get_time_approved(self, loan):
        if loan.time_approved is None:
            return loan.time_approved
        return loan.time_approved.strftime("%Y-%m-%d %H:%M:%S")

    def get_time_disbursed(self, loan):
        if loan.time_disbursed is None:
            return loan.time_disbursed
        return loan.time_disbursed.strftime("%Y-%m-%d %H:%M:%S")

    def get_time_of_last_payment(self, loan):
        if loan.time_of_last_payment is None:
            return loan.time_of_last_payment
        return loan.time_of_last_payment.strftime("%Y-%m-%d %H:%M:%S")

    def get_locked_shares(self, loan):
        try:
            ln = loan.locked.filter(shares_transaction__shares=loan.circle_member.shares.get())
            return ln[0].shares_transaction.num_of_shares
        except:
            return 0

class CircleAccNoSerializer(serializers.Serializer):
    """
    serializer to retrieve circle account number
    """
    circle_acc_number = serializers.CharField()

class LoanAmortizationSerializer(serializers.ModelSerializer):
    """
    serializer for saving schedule
    """
    total_monthly_repayment = serializers.CharField(source='total_repayment')
    repayment_date = serializers.SerializerMethodField()
    class Meta:
        model = LoanAmortizationSchedule
        fields = ['repayment_date', 'principal', 'interest', 'total_monthly_repayment']

    def get_repayment_date(self, amortization_schedule):
        return amortization_schedule.repayment_date.strftime("%Y-%m-%d")

class LoanTariffSerializer(serializers.ModelSerializer):
    """
    Serializer for circle loan tariff end point
    """
    class Meta:
        model = LoanTariff
        fields = ['min_amount', 'max_amount', 'num_of_months', 'monthly_interest_rate']

class LoanRepaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for loan repayment endpoint
    """
    is_fully_repaid = serializers.SerializerMethodField()
    loan_code = serializers.SerializerMethodField()
    time_of_repayment = serializers.SerializerMethodField()
    class Meta:
        model = LoanRepayment
        fields = ['time_of_repayment', 'amount', 'is_fully_repaid', 'loan_code']

    def get_time_of_repayment(self, loan_repayment):
        return loan_repayment.time_of_repayment.strftime("%Y-%m-%d %H:%M:%S")

    def get_is_fully_repaid(self, loan_repayment):
        if "is_fully_repaid" in self.context:
            return self.context.get("is_fully_repaid")
        return False

    def get_loan_code(self, loan_repayment):
        return loan_repayment.amortization_schedule.loan.loan_code

class StrictBooleanField(serializers.BooleanField):
    def from_native(self, value):
        if value in ('true', 't', 'True', '1'):
            return True
        if value in ('false', 'f', 'False', '0'):
            return False
        return None

class GuarantorResponseSerializer(serializers.Serializer):
    """
    Serializer for loan guarantor request loan
    """
    loan_code = serializers.CharField()
    has_accepted = StrictBooleanField()

class LoanCodeSerializer(serializers.Serializer):
    """
    Serializer for capturing loan code
    """
    loan_code = serializers.CharField()

class LoanGuarantorsSerializer(serializers.ModelSerializer):
    """
    Serializer for loan guarantors endpoint
    """
    status = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    amount = serializers.IntegerField(source='num_of_shares')

    class Meta:
        model = GuarantorRequest
        fields = ['phone_number', 'status', 'amount']

    def get_status(self, guarantor):
        if guarantor.has_accepted is None:
            return "pending"
        elif guarantor.has_accepted is True:
            return "accepted"
        else:
            return "declined"

    def get_phone_number(self, guarantor):
        return guarantor.circle_member.member.phone_number

class NewLoanGuarantorSerializer(serializers.Serializer):
    """
    Serializer for new loan guarantor
    """
    amount = serializers.IntegerField()
    phone_number = serializers.CharField()
    loan_code = serializers.CharField()

class CurrentLoanGuarantorSerializer(serializers.Serializer):
    """
    Serializer for current loan guarantor endpoint
    """
    phone_number = serializers.CharField()
    loan_code = serializers.CharField()

class UnprocessedGuarantorRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for unprocessed loan guarantor request_type
    """
    phone_number = serializers.SerializerMethodField()
    circle_acc_number = serializers.SerializerMethodField()
    loan_code = serializers.SerializerMethodField()
    amount = serializers.IntegerField(source='num_of_shares')
    num_of_months = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()

    class Meta:
        model = GuarantorRequest
        fields = ['phone_number', 'circle_acc_number', 'loan_code', 'amount', 'num_of_months', 'rating', 'estimated_earning']

    def get_phone_number(self, guarantor):
        return guarantor.loan.circle_member.member.phone_number

    def get_circle_acc_number(self, guarantor):
        return guarantor.circle_member.circle.circle_acc_number

    def get_loan_code(self, guarantor):
        return guarantor.loan.loan_code

    def get_num_of_months(self, guarantor):
        amount = guarantor.loan.amount
        try:
            loan_tariff = guarantor.loan.loan_tariff
            if loan_tariff is None:
                loan_tariff = LoanTariff.objects.get(circle=guarantor.circle_member.circle,
                                                     max_amount__gte=amount,
                                                     min_amount__lte=amount)
            return loan_tariff.num_of_months
        except LoanTariff.DoesNotExist:
            return 0

    def get_rating(self, guarantor):
        return loan_utils.Loan().calculate_circle_member_loan_rating(guarantor.loan.circle_member.member)

class LoanAmountSerializer(serializers.Serializer):
    """
    Serializer for loan amount endpoint
    """
    loan_amount = serializers.IntegerField()

class ProcessingFeeSerializer(serializers.ModelSerializer):
    """
    Serializer for processing fee endpoint
    """
    class Meta:
        model = LoanProcessingFee
        fields = ['processing_fee']
