import datetime
from circle.models import Circle, CircleMember
from shares.models import Shares, IntraCircleShareTransaction
from django.db.models import Sum



class CircleUtils:

    @staticmethod
    def get_num_of_circles():
        return Circle.objects.all().count()

    @staticmethod
    def get_num_of_circles_registered__by_day(search_date=None):
        if search_date is None:
            search_date = datetime.datetime.now()
        return Circle.objects.filter(time_initiated__range=(
                            datetime.datetime.combine(search_date, datetime.time.min),
                            datetime.datetime.combine(search_date, datetime.time.max))).count()

    @staticmethod
    def get_num_of_active_circles():
        return Circle.objects.filter(is_active=True).count()

    @staticmethod
    def get_circles_by_member(member):
        if not CircleMember.objects.filter(member=member).exists():
            return None
        else:
            circles = [obj.circle for obj in CircleMember.objects.filter(member=member)]
            return circles

    @staticmethod
    def get_all_circles():
        return Circle.objects.all()

    @staticmethod
    def get_num_of_circle_members(circle):
        return CircleMember.objects.filter(circle=circle).count()


    @staticmethod
    def get_total_shares_deposit(circle):
        deposits = IntraCircleShareTransaction.objects.filter(
            shares=Shares.objects.filter(circle=circle), transaction_type__icontains='DEPOSIT')\
            .aggregate(Sum('num_of_shares'))
        withdrawals = IntraCircleShareTransaction.objects.filter(
            shares=Shares.objects.filter(circle=circle), transaction_type__icontains='WITHDRAW')\
            .aggregate(Sum('num_of_shares'))
        return deposits









