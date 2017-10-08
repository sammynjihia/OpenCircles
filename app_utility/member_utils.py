from django.db.models import Sum
from member.models import Beneficiary,Member


class OpenCircleMember():
    def calculate_member_benefit(self,member):
        benefit = Beneficiary.objects.filter(member=member).aggregate(total=Sum('benefit'))
        if benefit['total'] is None:
            return 0
        total_benefit = benefit['total']*100
        return total_benefit

    def get_is_member(self,phone_number):
        try:
            Member.objects.get(phone_number=phone_number)
            return True
        except Member.DoesNotExist:
            return False
