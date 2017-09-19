from django.db.models import Sum
from member.models import Beneficiary


class OpenCircleMember():
    def calculate_member_benefit(self,member):
        benefit = Beneficiary.objects.filter(member=member).aggregate(total=Sum('benefit'))
        if benefit['total'] is None:
            return 0
        total_benefit = benefit['total']*100
        return total_benefit
