from rest_framework import serializers

from django.core.exceptions import ObjectDoesNotExist

from .models import Circle, CircleMember, AllowedGuarantorRequest, CircleInvitation, MGRCircle, MGRCircleCycle

from member.serializers import MemberSerializer
from member.models import Member

import app_utility


from loan.serializers import LoanTariffSerializer
from loan.models import LoanTariff
import base64

class CircleCreationSerializer(serializers.ModelSerializer):
    """
    Serializer for circle registration endpoint
    """
    contact_list = serializers.ListField()
    pin = serializers.CharField()
    loan_tariff = serializers.ListField()

    class Meta:
        model = Circle
        fields = ['circle_name', 'circle_type', 'contact_list', 'minimum_share', 'pin', 'loan_tariff']

    def create(self,validated_data):
        validated_data.pop('contact_list')
        validated_data.pop('pin')
        validated_data.pop('loan_tariff')
        # validated_data['circle_name'] = validated_data['circle_name'].lower()
        return Circle.objects.create(**validated_data)

class CircleInitCreationSerializer(serializers.ModelSerializer):
    """
    serializer for initiative registration endpoint
    """
    contact_list = serializers.ListField()
    pin = serializers.CharField()

    class Meta:
        model = Circle
        fields = ['circle_name', 'contact_list', 'circle_type', 'description', 'pin']

    def create(self, validated_data):
        validated_data.pop('contact_list')
        validated_data.pop('pin')
        return Circle.objects.create(**validated_data)

class CircleMGRCreationSerializer(serializers.ModelSerializer):
    """
    serializer for merry go round  registration endpoint
    """
    circle_name = serializers.CharField(source='circle.circle_name')
    circle_type = serializers.CharField(source='circle.circle_model_type')
    contribution_schedule = serializers.ChoiceField(source='schedule', choices=['WEEKLY', 'MONTHLY'])
    contribution_day = serializers.ChoiceField(source='day', choices=MGRCircle.DAY_CHOICES, required=False)
    contact_list = serializers.ListField()
    pin = serializers.CharField()

    class Meta:
        model = MGRCircle
        fields = ['circle_name', 'circle_type', 'contribution_schedule', 'contribution_day',
                  'amount', 'fine', 'contact_list', 'pin']

    def create(self, validated_data):
        print(validated_data)
        validated_data.pop('contact_list')
        validated_data.pop('pin')
        circle_data = validated_data.pop('circle')
        initiated_by, circle_acc_number = validated_data.pop('initiated_by'), validated_data.pop('circle_acc_number')
        circle = Circle.objects.create(initiated_by=initiated_by, circle_acc_number=circle_acc_number, **circle_data)
        MGRCircle.objects.create(circle=circle, **validated_data)
        return circle

class CircleSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for circle listing endpoint
    """
    initiated_by = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    date_created = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    is_invited = serializers.SerializerMethodField()
    invited_by = serializers.SerializerMethodField()
    loan_limit = serializers.SerializerMethodField()
    loan_tariff = serializers.SerializerMethodField()
    circle_type = serializers.SerializerMethodField()

    class Meta:
        model = Circle
        fields = ['circle_name', 'circle_type', 'circle_acc_number', 'is_active', 'is_member', 'is_invited',
                  'invited_by', 'members', 'initiated_by', 'date_created', 'minimum_share', 'loan_limit',
                  'member_count', 'loan_tariff']

    def get_member_count(self, circle):
        return CircleMember.objects.filter(circle_id=circle.id).count()

    def get_initiated_by(self, circle):
        return Member.objects.get(id=circle.initiated_by_id).user.email

    def get_date_created(self, circle):
        date =  circle.time_initiated
        return date.strftime("%Y-%m-%d %H:%M:%S")

    def get_loan_tariff(self, circle):
        loan_tariff = LoanTariff.objects.filter(circle=circle)
        if loan_tariff.exists():
            loan_tariff_serializer = LoanTariffSerializer(loan_tariff, many=True)
            return loan_tariff_serializer.data
        return []

    def get_members(self, circle):
        members_ids = CircleMember.objects.filter(circle_id=circle.id).values_list('member', flat=True)
        members = Member.objects.filter(id__in=members_ids).select_related('user')
        serializer = CircleMemberSerializer(members,many=True, context={"request":self.context.get('request'), "circle":circle})
        return serializer.data

    def get_is_member(self, circle):
        try:
            CircleMember.objects.get(circle=circle, member=self.context.get('request').user.member)
            return True
        except CircleMember.DoesNotExist:
            return False

    def get_is_invited(self, circle):
        # ids = CircleMember.objects.filter(circle=circle).values_list('id',flat=True)
        circle_invite = CircleInvitation.objects.filter(
                                                    phone_number=self.context.get('request').user.member.phone_number,
                                                    invited_by__circle=circle).exists()
        if circle_invite:
            return True
        else:
            return False

    def get_invited_by(self, circle):
        try:
            circle_invite = CircleInvitation.objects.get(
                                                        phone_number=self.context.get('request').user.member.phone_number,
                                                        invited_by__circle=circle)
            user = circle_invite.invited_by.member.user
            invited_by = "{} {}".format(user.first_name, user.last_name)
            return invited_by
        except CircleInvitation.DoesNotExist:
            return ''

    def get_loan_limit(self, circle):
        member = self.context.get('request').user.member
        loan_instance = app_utility.loan_utils.Loan()
        loan_limit = loan_instance.calculate_loan_limit(circle, member)
        return loan_limit

    def get_circle_type(self, circle):
        return circle.circle_model_type

class CircleInitSerializer(serializers.ModelSerializer):
    """
    Serializer for circle listing endpoint
    """
    initiated_by = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    date_created = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    is_invited = serializers.SerializerMethodField()
    invited_by = serializers.SerializerMethodField()
    circle_type = serializers.SerializerMethodField()

    class Meta:
        model = Circle
        fields = ['circle_name', 'circle_type', 'circle_acc_number', 'description', 'is_active', 'is_member', 'is_invited',
                  'invited_by', 'members', 'initiated_by', 'date_created', 'member_count']

    def get_member_count(self, circle):
        return CircleMember.objects.filter(circle_id=circle.id).count()

    def get_initiated_by(self, circle):
        return Member.objects.get(id=circle.initiated_by_id).user.email

    def get_date_created(self, circle):
        date =  circle.time_initiated
        return date.strftime("%Y-%m-%d %H:%M:%S")

    def get_members(self, circle):
        members_ids = CircleMember.objects.filter(circle_id=circle.id).values_list('member', flat=True)
        members = Member.objects.filter(id__in=members_ids).select_related('user')
        serializer = CircleMemberSerializer(members,many=True, context={"request":self.context.get('request'), "circle":circle})
        return serializer.data

    def get_is_member(self, circle):
        try:
            CircleMember.objects.get(circle=circle, member=self.context.get('request').user.member)
            return True
        except CircleMember.DoesNotExist:
            return False

    def get_is_invited(self, circle):
        # ids = CircleMember.objects.filter(circle=circle).values_list('id',flat=True)
        circle_invite = CircleInvitation.objects.filter(
                                                    phone_number=self.context.get('request').user.member.phone_number,
                                                    invited_by__circle=circle).exists()
        if circle_invite:
            return True
        else:
            return False

    def get_invited_by(self, circle):
        try:
            circle_invite = CircleInvitation.objects.get(
                                                        phone_number=self.context.get('request').user.member.phone_number,
                                                        invited_by__circle=circle)
            user = circle_invite.invited_by.member.user
            invited_by = "{} {}".format(user.first_name, user.last_name)
            return invited_by
        except CircleInvitation.DoesNotExist:
            return ''

    def get_circle_type(self, circle):
        return circle.circle_model_type

class CircleMGRSerializer(serializers.ModelSerializer):
    """
    Serializer for circle listing endpoint
    """
    initiated_by = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    date_created = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    is_invited = serializers.SerializerMethodField()
    invited_by = serializers.SerializerMethodField()
    contribution_schedule = serializers.SerializerMethodField()
    contribution_day = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    fine = serializers.SerializerMethodField()
    circle_type = serializers.SerializerMethodField()
    disbursal_date = serializers.SerializerMethodField()
    recipient = serializers.SerializerMethodField()

    class Meta:
        model = Circle
        fields = ['circle_name', 'circle_type', 'circle_acc_number', 'contribution_schedule', 'contribution_day',
                  'amount', 'fine', 'is_active', 'is_member', 'is_invited', 'invited_by', 'members', 'initiated_by',
                  'date_created', 'member_count', 'disbursal_date', 'recipient']

    def get_member_count(self, circle):
        print('count')
        return CircleMember.objects.filter(circle_id=circle.id).count()

    def get_initiated_by(self, circle):
        return circle.initiated_by.user.email

    def get_date_created(self, circle):
        date =  circle.time_initiated
        return date.strftime("%Y-%m-%d %H:%M:%S")

    def get_members(self, circle):
        members_ids = CircleMember.objects.filter(circle_id=circle.id).values_list('member', flat=True)
        members = Member.objects.filter(id__in=members_ids).select_related('user')
        serializer = CircleMGRMemberSerializer(members, many=True, context={"request":self.context.get('request'), "circle":circle})
        return serializer.data

    def get_is_member(self, circle):
        try:
            CircleMember.objects.get(circle=circle, member=self.context.get('request').user.member)
            return True
        except CircleMember.DoesNotExist:
            return False

    def get_is_invited(self, circle):
        # ids = CircleMember.objects.filter(circle=circle).values_list('id',flat=True)
        circle_invite = CircleInvitation.objects.filter(
                                                    phone_number=self.context.get('request').user.member.phone_number,
                                                    invited_by__circle=circle).exists()
        if circle_invite:
            return True
        else:
            return False

    def get_invited_by(self, circle):
        try:
            circle_invite = CircleInvitation.objects.get(
                                                        phone_number=self.context.get('request').user.member.phone_number,
                                                        invited_by__circle=circle)
            user = circle_invite.invited_by.member.user
            invited_by = "{} {}".format(user.first_name, user.last_name)
            return invited_by
        except CircleInvitation.DoesNotExist:
            return ''

    def get_contribution_schedule(self, circle):
        return circle.mgr_circle.get().schedule

    def get_contribution_day(self, circle):
        return circle.mgr_circle.get().day

    def get_amount(self, circle):
        return circle.mgr_circle.get().amount

    def get_fine(self, circle):
        return circle.mgr_circle.get().fine

    def get_circle_type(self, circle):
        return circle.circle_model_type

    def get_disbursal_date(self, circle):
        cycle = MGRCircleCycle.objects.filter(circle_member__circle=circle, is_complete=False)
        if cycle.exists():
            return cycle[0].disbursal_date.strftime("%Y-%m-%d")
        return

    def get_recipient(self, circle):
        cycle = MGRCircleCycle.objects.filter(circle_member__circle=circle, is_complete=False)
        if cycle.exists():
            return cycle[0].circle_member.member.phone_number
        return

class InvitedCircleSerializer(serializers.ModelSerializer):
    """
    Serializer for circle listing endpoint
    """
    initiated_by = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    date_created = serializers.SerializerMethodField()
    # members = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    is_invited = serializers.SerializerMethodField()
    invited_by = serializers.SerializerMethodField()
    loan_tariff = serializers.SerializerMethodField()
    circle_type = serializers.SerializerMethodField()

    class Meta:
        model = Circle
        fields = ['circle_name', 'circle_type', 'circle_acc_number', 'is_active', 'is_member', 'is_invited',
                  'invited_by', 'initiated_by', 'date_created', 'minimum_share',
                  'loan_tariff', 'member_count']

    def get_member_count(self, circle):
        return CircleMember.objects.filter(circle_id=circle.id).count()

    def get_initiated_by(self, circle):
        return Member.objects.get(id=circle.initiated_by_id).user.email

    def get_date_created(self, circle):
        date =  circle.time_initiated
        return date.strftime("%Y-%m-%d %H:%M:%S")

    # def get_members(self, circle):
    #     members_ids = CircleMember.objects.filter(circle=circle).values_list('member', flat=True)
    #     members = Member.objects.filter(id__in=members_ids).select_related('user')
    #     serializer = UnloggedCircleMemberSerializer(members, many=True, context={"circle":circle})
    #     return serializer.data

    def get_is_member(self, circle):
        return False

    def get_is_invited(self, circle):
        return True

    def get_invited_by(self, circle):
        return self.context.get('invited_by')

    def get_loan_tariff(self, circle):
        loan_tariff = LoanTariff.objects.filter(circle=circle)
        if loan_tariff.exists():
            loan_tariff_serializer = LoanTariffSerializer(loan_tariff, many=True)
            return loan_tariff_serializer.data
        return []

    def get_circle_type(self, circle):
        return circle.circle_model_type

class InvitedMGRCircleSerializer(serializers.ModelSerializer):
    """
    Serializer for MGR invited member endpoint
    """
    initiated_by = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    date_created = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    is_invited = serializers.SerializerMethodField()
    invited_by = serializers.SerializerMethodField()
    contribution_schedule = serializers.SerializerMethodField()
    contribution_day = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    fine = serializers.SerializerMethodField()
    circle_type = serializers.SerializerMethodField()

    class Meta:
        model = Circle
        fields = ['circle_name', 'circle_type', 'circle_acc_number', 'is_active', 'is_member', 'is_invited',
                  'invited_by', 'initiated_by', 'date_created', 'member_count', 'contribution_schedule',
                  'contribution_day', 'amount', 'fine']

    def get_member_count(self, circle):
        return CircleMember.objects.filter(circle_id=circle.id).count()

    def get_initiated_by(self, circle):
        return Member.objects.get(id=circle.initiated_by_id).user.email

    def get_date_created(self, circle):
        date =  circle.time_initiated
        return date.strftime("%Y-%m-%d %H:%M:%S")

    def get_is_member(self, circle):
        return False

    def get_is_invited(self, circle):
        return True

    def get_invited_by(self, circle):
        return self.context.get('invited_by')

    def get_contribution_schedule(self, circle):
        return circle.mgr_circle.get().schedule

    def get_contribution_day(self, circle):
        return circle.mgr_circle.get().day

    def get_amount(self, circle):
        return circle.mgr_circle.get().amount

    def get_fine(self, circle):
        return circle.mgr_circle.get().fine

    def get_circle_type(self, circle):
        return circle.circle_model_type

class CircleInvitationSerializer(serializers.Serializer):
    """
    Serializer for circle invitation response
    """
    circle_acc_number = serializers.CharField()

class AllowedGuaranteeSerializer(serializers.Serializer):
    """
    Serializer for allowed guarantor request setting endpoint
    """
    guarantee = serializers.CharField()
    circle_acc_number = serializers.CharField()

class AllowedGuaranteeRequestSerializer(serializers.Serializer):
    """
    Serializer for allowed guarantor setting
    """
    allow_public_guarantees = serializers.CharField()
    circle_acc_number = serializers.CharField()

    class Meta:
        fields = ['allow_public_guarantees', 'circle_acc_number']

class JoinCircleSerializer(serializers.Serializer):
    """
    Serializer for join circle endpoint
    """
    amount = serializers.IntegerField()
    pin = serializers.CharField()
    circle_acc_number = serializers.CharField()

    class Meta:
        field = ['amount', 'pin', 'circle_acc_number']

class JoinInitCircleSerializer(serializers.Serializer):
    """
    Serializer for joining init circle endpoint
    """
    pin = serializers.CharField()
    circle_acc_number = serializers.CharField()

    class Meta:
        field = ['pin', 'circle_acc_number']

class JoinMGRCircleSerializer(serializers.Serializer):
    """
    Serializer for joining MGR circle endpoint
    """
    pin = serializers.CharField()
    circle_acc_number = serializers.CharField()

    class Meta:
        field = ['pin', 'circle_acc_number']

class CircleMemberSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    surname = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    # passport_image = serializers.SerializerMethodField()
    # date_of_birth = serializers.SerializerMethodField()
    time_registered = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()
    available_shares = serializers.SerializerMethodField()
    allow_guarantor_request = serializers.SerializerMethodField()
    allow_public_guarantees_request = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ['first_name', 'surname', 'other_name', 'email', 'gender', 'country', 'phone_number', 'national_id',
                  'currency', 'date_of_birth', 'time_registered', 'is_self', 'available_shares',
                  'allow_guarantor_request', 'allow_public_guarantees_request', 'is_active', 'is_admin']

    def get_time_registered(self, member):
         date = member.time_registered
         return date.strftime("%Y-%m-%d %H:%M:%S")

    def get_is_self(self, member):
        request = self.context.get('request')
        is_self = True if request.user.member.national_id == member.national_id else False
        return is_self

    def get_is_active(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.is_active

    def get_available_shares(self, member):
        circle = self.context.get('circle')
        instance = app_utility.circle_utils.Circle()
        available_shares = instance.get_available_circle_member_shares(circle, member)
        return available_shares

    def get_allow_guarantor_request(self, member):
        request, circle = self.context.get('request'), self.context.get('circle')
        try:
            user = CircleMember.objects.get(member=request.user.member, circle=circle)
        except CircleMember.DoesNotExist:
            return False
        circle_member = CircleMember.objects.get(member=member, circle=circle)
        if AllowedGuarantorRequest.objects.filter(circle_member=circle_member).exists():
            try:
                AllowedGuarantorRequest.objects.get(circle_member=circle_member, allows_request_from=user)
                return True
            except ObjectDoesNotExist:
                return False
        return True

    def get_allow_public_guarantees_request(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.allow_public_guarantees_request

    def get_is_admin(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.is_admin

    # def get_passport_image(self,member):
    #     if member.passport_image:
    #         # f = open(member.passport_image.path, 'rb')
    #         # image = File(f)
    #         # data = base64.b64encode(image.read())
    #         # f.close()
    #         with open(member.passport_image.path, "rb") as image_file:
    #             encoded_string = base64.b64encode(image_file.read())
    #         with open('image_file.txt', 'w') as post_file:
    #             post_file.write(str(encoded_string))
    #         print(encoded_string)
    #         return encoded_string
    #     else:
    #         return ''
    # def get_guarantees(self,member):
    #     value = self.get_allow_public_guarantees_request(member)
    #     circle = self.context.get('circle')
    #     members = {}
    #     if not value:
    #         guarantees_ids = AllowedGuarantorRequest(circle_member=CircleMember.objects.get(circle=circle,member=member)).values_list('circle_member',flat=True)
    #         guarantees = Member.objects.filter(id__in=CircleMember.objects.filter(id__in=guarantees).values_list('member',flat=True))
    #         member_serializer = MemberSerializer(guarantees,many=True)
    #         return member_serializer.data
    #     return members

class CircleInitMemberSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    surname = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    # passport_image = serializers.SerializerMethodField()
    # date_of_birth = serializers.SerializerMethodField()
    time_registered = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()
    member_contributions = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ['first_name', 'surname', 'other_name', 'email', 'gender', 'country', 'phone_number', 'national_id',
                  'currency', 'date_of_birth', 'time_registered', 'is_self', 'member_contributions', 'is_active', 'is_admin']

    def get_time_registered(self, member):
         date = member.time_registered
         return date.strftime("%Y-%m-%d %H:%M:%S")

    def get_is_self(self, member):
        request = self.context.get('request')
        is_self = True if request.user.member.national_id == member.national_id else False
        return is_self

    def get_is_active(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.is_active

    def get_is_admin(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.is_admin

    def get_member_contributions(self, member):
        circle = self.context.get('circle')
        instance = app_utility.circle_utils.Circle()
        total_contributions = instance.get_total_circle_member_shares(circle, member, None)
        return total_contributions

class CircleMGRMemberSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    surname = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    time_registered = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()
    member_contributions = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    is_next = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ['first_name', 'surname', 'other_name', 'email', 'gender', 'country', 'phone_number', 'national_id',
                  'currency', 'date_of_birth', 'time_registered', 'is_self', 'member_contributions', 'is_active',
                  'is_admin', 'priority', 'is_next']

    def get_time_registered(self, member):
         date = member.time_registered
         return date.strftime("%Y-%m-%d %H:%M:%S")

    def get_is_self(self, member):
        request = self.context.get('request')
        is_self = True if request.user.member.national_id == member.national_id else False
        return is_self

    def get_is_active(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.is_active

    def get_is_admin(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.is_admin

    def get_member_contributions(self, member):
        circle = self.context.get('circle')
        instance = app_utility.circle_utils.Circle()
        total_contributions = instance.get_total_circle_member_shares(circle, member, None)
        return total_contributions

    def get_priority(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.priority

    def get_is_next(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        circle_cycle = MGRCircleCycle.objects.filter(circle_member=circle_member,
                                                     is_complete=False)
        if circle_cycle.exists():
            return True
        return False


class UnloggedCircleMemberSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    surname = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    # passport_image = serializers.SerializerMethodField()
    # date_of_birth = serializers.SerializerMethodField()
    time_registered = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()
    available_shares = serializers.SerializerMethodField()
    allow_public_guarantees_request = serializers.SerializerMethodField()
    allow_guarantor_request = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ['first_name', 'surname', 'other_name', 'email', 'gender', 'country', 'phone_number',
                  'national_id', 'currency', 'date_of_birth', 'time_registered', 'is_self', 'available_shares',
                  'allow_public_guarantees_request', 'allow_guarantor_request', 'is_active', 'is_admin']

    def get_time_registered(self, member):
         date = member.time_registered
         return date.strftime("%Y-%m-%d %H:%M:%S")

    def get_is_self(self, member):
        is_self = False
        return is_self

    def get_is_active(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.is_active

    def get_available_shares(self, member):
        circle = self.context.get('circle')
        instance = app_utility.circle_utils.Circle()
        available_shares = instance.get_available_circle_member_shares(circle, member)
        return available_shares

    def get_allow_public_guarantees_request(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.allow_public_guarantees_request

    def get_allow_guarantor_request(self, member):
        response = self.get_allow_public_guarantees_request(member)
        if response:
            return True
        return False

    def get_is_admin(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.is_admin
    # def get_passport_image(self,member):
    #     if member.passport_image:
    #         # f = open(member.passport_image.path, 'rb')
    #         # image = File(f)
    #         # data = base64.b64encode(image.read())
    #         # f.close()
    #         with open(member.passport_image.path, "rb") as image_file:
    #             encoded_string = base64.b64encode(image_file.read())
    #         with open('image_file.txt', 'w') as post_file:
    #             post_file.write(str(encoded_string))
    #         print(encoded_string)
    #         return encoded_string
    #     else:
    #         return ''
    # def get_guarantees(self,member):
    #     value = self.get_allow_public_guarantees_request(member)
    #     circle = self.context.get('circle')
    #     members = {}
    #     if not value:
    #         guarantees_ids = AllowedGuarantorRequest(circle_member=CircleMember.objects.get(circle=circle,member=member)).values_list('circle_member',flat=True)
    #         guarantees = Member.objects.filter(id__in=CircleMember.objects.filter(id__in=guarantees).values_list('member',flat=True))
    #         member_serializer = MemberSerializer(guarantees,many=True)
    #         return member_serializer.data
    #     return members

class UnloggedInitCircleMemberSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    surname = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    # passport_image = serializers.SerializerMethodField()
    # date_of_birth = serializers.SerializerMethodField()
    time_registered = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()
    member_contributions = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ['first_name', 'surname', 'other_name', 'email', 'gender', 'country', 'phone_number',
                  'national_id', 'currency', 'date_of_birth', 'time_registered', 'is_self', 'member_contributions',
                  'is_active', 'is_admin']


    def get_time_registered(self, member):
         date = member.time_registered
         return date.strftime("%Y-%m-%d %H:%M:%S")

    def get_is_self(self, member):
        is_self = False
        return is_self

    def get_is_active(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.is_active

    def get_is_admin(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.is_admin

    def get_member_contributions(self, member):
        circle = self.context.get('circle')
        instance = app_utility.circle_utils.Circle()
        total_contributions = instance.get_total_circle_member_shares(circle, member, None)
        return total_contributions

class UnloggedMGRCircleMemberSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    surname = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    time_registered = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()
    member_contributions = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    is_next = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ['first_name', 'surname', 'other_name', 'email', 'gender', 'country', 'phone_number',
                  'national_id', 'currency', 'date_of_birth', 'time_registered', 'is_self', 'member_contributions',
                  'is_active', 'is_admin', 'priority', 'is_next']

    def get_time_registered(self, member):
         date = member.time_registered
         return date.strftime("%Y-%m-%d %H:%M:%S")

    def get_is_self(self, member):
        is_self = False
        return is_self

    def get_is_active(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.is_active

    def get_is_admin(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.is_admin

    def get_member_contributions(self, member):
        circle = self.context.get('circle')
        instance = app_utility.circle_utils.Circle()
        total_contributions = instance.get_total_circle_member_shares(circle, member, None)
        return total_contributions

    def get_priority(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        return circle_member.priority

    def get_is_next(self, member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(circle=circle, member=member)
        circle_cycle = MGRCircleCycle.objects.filter(circle_member=circle_member,
                                                     is_complete=False)
        if circle_cycle.exists():
            return True

        else:
            if circle_member.priority == 1:
                return True
        return False

class CircleInviteSerializer(serializers.Serializer):
    """
    Serializer for circle invites endpoint
    """
    phone_number = serializers.CharField()
    circle_acc_number = serializers.CharField()

class CircleMemberDetailsSerializer(serializers.Serializer):
    """
    Serializer for circle member details endpoint
    """
    phone_number = serializers.CharField()
    circle_acc_number = serializers.CharField()

class CircleMemberGuaranteeSerializer(serializers.Serializer):
    """
    Serializer for circle member guarantee list
    """
    circle_acc_number = serializers.CharField()

class CircleNameSerializer(serializers.ModelSerializer):
    """
    Serializer for circle name endpoint
    """
    class Meta:
        model = Circle
        fields = ['circle_name']

class CircleAccNumberSerializer(serializers.Serializer):
    """
    Serializer for circle acc number endpoint
    """
    circle_acc_number = serializers.CharField()

class AdminCircleInviteResponse(serializers.Serializer):
    """
    Serializer for admin circle invite response
    """
    circle_acc_number = serializers.CharField()
    invitee_phone_number = serializers.CharField()
    is_allowed = serializers.CharField()

class CircleInvitesSerializer(serializers.ModelSerializer):
    """
    Serializer for circle invites
    """
    circle_acc_number = serializers.SerializerMethodField()
    invited_by = serializers.SerializerMethodField()
    invitee = serializers.SerializerMethodField()

    class Meta:
        model = CircleInvitation
        fields = ['circle_acc_number', 'invited_by', 'invitee']

    def get_circle_acc_number(self, circle_invite):
        return circle_invite.invited_by.circle.circle_acc_number

    def get_invited_by(self, circle_invite):
        return circle_invite.invited_by.member.phone_number

    def get_invitee(self, circle_invite):
        return circle_invite.phone_number

