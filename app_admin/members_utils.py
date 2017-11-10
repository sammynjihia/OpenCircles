import datetime

from django.db.models import Q
from member.models import Member, Beneficiary
from django.contrib.auth.models import User
from app_utility import sms_utils



class MemberUtils:

    @staticmethod
    def get_num_of_members():
        return Member.objects.all().count()

    @staticmethod
    def get_num_of_members_registered__by_day(search_date=None):
        if search_date is None:
            search_date = datetime.date.today()
        return Member.objects.filter(time_registered__range=(
                            datetime.datetime.combine(search_date, datetime.time.min),
                            datetime.datetime.combine(search_date, datetime.time.max))).count()

    @staticmethod
    def get_all_members():
        return Member.objects.all()

    @staticmethod
    def search_for_member(search_val):
        search_val = search_val.strip()
        sms = sms_utils.Sms()
        members_obj = Member.objects.filter(
            Q(Q(national_id=search_val) | Q(phone_number=sms.format_phone_number(search_val)))
        )
        return members_obj

    @staticmethod
    def get_member_from_id(id):
        if not Member.objects.filter(id=id).exists():
            return None
        return Member.objects.get(id=id)

    @staticmethod
    def get_next_of_kin(member):
        if Beneficiary.objects.filter(member=member).exists():
            return Beneficiary.objects.get(member_id=member.id)
        else:
            return None








    




