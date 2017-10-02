from rest_framework import serializers
from loan.models import LoanApplication,LoanTariff,LoanRepayment
from circle.models import Circle


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
        fields = ['amount','pin','loan_code']

class LoansSerializer(serializers.ModelSerializer):
    """
    Serializer for loan listing endpoint
    """
    time_of_application = serializers.SerializerMethodField()
    time_approved = serializers.SerializerMethodField()
    time_disbursed = serializers.SerializerMethodField()
    time_of_last_payment = serializers.SerializerMethodField()
    class Meta:
        model = LoanApplication
        fields = ['amount','loan_code','interest_rate','num_of_repayment_cycles','time_of_application', 'is_approved', 'time_approved','is_disbursed','time_disbursed','is_fully_repaid', 'time_of_last_payment']

    def get_time_of_application(self,loan):
        return loan.time_of_application.strftime("%Y-%m-%d %H:%M:%S")

    def get_time_approved(self,loan):
        if loan.time_approved is None:
            return loan.time_approved
        return loan.time_approved.strftime("%Y-%m-%d %H:%M:%S")

    def get_time_disbursed(self,loan):
        if loan.time_disbursed is None:
            return loan.time_disbursed
        return loan.time_disbursed.strftime("%Y-%m-%d %H:%M:%S")

    def get_time_of_last_payment(self,loan):
        if loan.time_of_last_payment is None:
            return loan.time_of_last_payment
        return loan.time_of_last_payment.strftime("%Y-%m-%d %H:%M:%S")

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
        model = "LoanAmortizationSchedule"
        fields = ['repayment_date','principal','interest','total_monthly_repayment']

    def get_repayment_date(self,amortization_schedule):
        return amortization_schedule.repayment_date.strftime("%Y-%m-%d")

class LoanTariffSerializer(serializers.ModelSerializer):
    """
    Serializer for circle loan tariff end point
    """
    class Meta:
        model = LoanTariff
        fields = ['min_amount','max_amount','num_of_months','monthly_interest_rate']

class LoanRepaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for loan repayment endpoint
    """
    is_fully_repaid = serializers.SerializerMethodField()
    loan_code = serializers.CharField(source="loan.loan_code")
    time_of_repayment = serializers.SerializerMethodField()
    class Meta:
        model = LoanRepayment
        fields = ['time_of_repayment','amount','is_fully_repaid','loan_code']

    def get_time_of_repayment(self,loan_repayment):
        return loan_repayment.time_of_repayment.strftime("%Y-%m-%d %H:%M:%S")

    def get_is_fully_repaid(self,loan_repayment):
        if "is_fully_repaid" in self.context:
            return self.context.get("is_fully_repaid")
        return False

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
