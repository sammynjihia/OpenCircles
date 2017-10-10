from django.db.models import Sum
from member.models import Member
from circle.models import Circle as CircleModel,CircleMember,CircleInvitation
from shares.models import Shares,IntraCircleShareTransaction
from loan.models import LoanTariff,GuarantorRequest

import operator,re

class Circle():
    def get_suggested_circles(self,unjoined_circles,contacts):
        suggested_circles={}
        unjoined_circles = unjoined_circles.filter(circle_type="OPEN")
        for circle in unjoined_circles:
            circle_count = CircleMember.objects.filter(circle=circle,member_id__in=Member.objects.filter(phone_number__in=contacts).values_list('id',flat=True)).count()
            suggested_circles[circle]=circle_count
        suggested_circles = sorted(suggested_circles.items(),key=operator.itemgetter(1),reverse=True)[0:5]
        return suggested_circles

    def check_update_circle_status(self,circle):
        if not circle.is_active:
            if CircleMember.objects.filter(circle=circle).count() >= 5:
                circle.is_active=True
                circle.save()
                return True
            return False
        return True

    def get_invited_circles(self,request,unjoined_circles):
        circle_members = CircleInvitation.objects.filter(phone_number=request.user.member.phone_number).values_list("invited_by",flat=True)
        circles_ids = CircleMember.objects.filter(id__in=circle_members).values_list('circle',flat=True)
        circles = CircleModel.objects.filter(id__in = circles_ids).order_by('id').distinct('id')
        invited_circles = [circle for circle in circles if circle in unjoined_circles]
        return invited_circles

    def get_available_circle_shares(self,circle):
        shares = Shares.objects.filter(circle_member__in=CircleMember.objects.filter(circle=circle))
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
        available_shares = (total_deposits-total_transfers-total_withdraws)-(total_locked-total_unlocked)
        return available_shares

    def get_available_circle_member_shares(self,circle,member):
        try:
            circle_member = CircleMember.objects.get(circle=circle,member=member)
        except CircleMember.DoesNotExist:
            return 0
        share = circle_member.shares.get()
        transactions = IntraCircleShareTransaction.objects.filter(shares=share)
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
        available_shares = (total_deposits-total_transfers-total_withdraws)-(total_locked-total_unlocked)
        return available_shares

    def get_guarantor_available_shares(self,circle,member):
        actual_available_shares = self.get_available_circle_member_shares(circle,member)
        circle_member = CircleMember.objects.get(circle=circle,member=member)
        requests = GuarantorRequest.objects.filter(circle_member=circle_member,has_accepted=None)
        if requests.exists():
            amount = requests.aggregate(total=Sum('num_of_shares'))
            return actual_available_shares - amount['total']
        return actual_available_shares

    def save_loan_tariff(self,circle,loan_data):
        loan_tariffs = [LoanTariff(max_amount=int(self.extract_amount(data["range"])[1]),min_amount=int(self.extract_amount(data["range"])[0]),num_of_months=data['months'],monthly_interest_rate=data['interest'],circle=circle) for data in loan_data]
        loan_tariffs = LoanTariff.objects.bulk_create(loan_tariffs)
        return loan_tariffs

    def extract_amount(self,loan_range):
        new_range = re.findall(r'\d+',loan_range)
        return new_range
