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
        return Member.objects.all().order_by('-time_registered')

    @staticmethod
    def search_for_member(search_val):
        search_val = search_val.strip()
        sms = sms_utils.Sms()
        members_obj = Member.objects.filter(
            Q(Q(national_id=search_val) | Q(phone_number=sms.format_phone_number(search_val)))
        )
        return members_obj

    @staticmethod
    def get_daily_registrations_count(start_date, end_date):

        print(start_date)
        print(end_date)

        if start_date is None:
            end_date = datetime.datetime.today()
            start_date = end_date - datetime.timedelta(days=7)

        members = Member.objects.filter(time_registered__range=(datetime.datetime.combine(start_date,
                                                                                          datetime.time.min),
                    datetime.datetime.combine(end_date, datetime.time.max))).order_by('time_registered')
        total_male = members.filter(gender='Male').count()
        total_female = members.filter(gender='Female').count()
        daily_registrations = []
        current_day = members.first().time_registered.day
        current_month = members.first().time_registered.month
        current_year = members.first().time_registered.year
        for obj in members:
            if obj.time_registered.day is not current_day or obj is members.first():
                current_day = obj.time_registered.day
                current_month = obj.time_registered.month
                current_year = obj.time_registered.year
                num_of_members = members.filter(time_registered__day=current_day,
                                                time_registered__month=current_month,
                                                time_registered__year=current_year).count()
                daily_registrations.append({
                    'day': obj.time_registered.strftime('%Y-%m-%d'),
                    'num_of_members': num_of_members
                })
            else:
                continue
        print(daily_registrations)
        return {
            'members': members,
            'start_date': start_date,
            'end_date': end_date,
            'daily_registrations': daily_registrations,
            'grouping_by_gender': {
                'male': total_male,
                'female': total_female
            }
        }


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








    




