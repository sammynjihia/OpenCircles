from rest_framework import serializers

from .models import Circle,CircleMember,AllowedGuarantorRequest,CircleInvitation

from member.serializers import MemberSerializer
from member.models import Member,Contacts

from shares.models import LockedShares

from django.db.models import Q

class CircleCreationSerializer(serializers.ModelSerializer):
    """
    Serializer for circle registration endpoint
    """
    contact_list = serializers.ListField()
    class Meta:
        model = Circle
        fields = ['circle_name','circle_type','contact_list','minimum_share']

    def create(self,validated_data):
        validated_data.pop('contact_list')
        # validated_data['circle_name'] = validated_data['circle_name'].lower()
        return Circle.objects.create(**validated_data)

class CircleSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for circle listing endpoint
    """
    initiated_by = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    date_created = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    phonebook_member_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    is_invited = serializers.SerializerMethodField()
    class Meta:
        model = Circle
        fields = ['circle_name','circle_type','circle_acc_number','is_active','is_member','is_invited','members','initiated_by','date_created','minimum_share','annual_interest_rate','member_count','phonebook_member_count']

    def get_member_count(self,circle):
        return CircleMember.objects.filter(circle_id=circle.id).count()

    def get_initiated_by(self,circle):
        return Member.objects.get(id=circle.initiated_by_id).user.email

    def get_is_active(self,circle):
        stat = 1 if circle.is_active else 0
        return stat

    def get_date_created(self,circle):
        return circle.time_initiated.date()

    def get_members(self,circle):
        members_ids = CircleMember.objects.filter(circle_id=circle.id).values_list('member',flat=True)
        members = Member.objects.filter(id__in=members_ids).select_related('user')
        serializer = CircleMemberSerializer(members,many=True,context={"request":self.context.get('request'),"circle":circle})
        return serializer.data

    def get_phonebook_member_count(self,circle):
        member = self.context.get('request').user.member
        contacts = Contacts.objects.filter(member=member,is_member=True).values_list('phone_number',flat=True)
        count = 0
        if contacts.count() > 0:
            count = CircleMember.objects.filter(circle=circle,member_id__in=Member.objects.filter(phone_number__in=contacts).values_list('id',flat=True)).count()
        return count

    def get_is_member(self,circle):
        try:
            CircleMember.objects.get(circle=circle,member=self.context.get('request').user.member)
            return 1
        except CircleMember.DoesNotExist:
            return 0

    def get_is_invited(self,circle):
        ids = CircleMember.objects.filter(circle=circle).values_list('id',flat=True)
        if CircleInvitation.objects.filter(phone_number=self.context.get('request').user.member.phone_number,invited_by__in=ids).exists():
            return 1
        else:
            return 0

class CircleInvitationSerializer(serializers.Serializer):
    """
    Serializer for circle invitation response
    """
    invite_id = serializers.CharField()
    invite_response = serializers.ChoiceField(choices=['A','D'])

class AllowedGuarantorRequestSerializer(serializers.Serializer):
    """
    Serializer for allowed guarantor request setting endpoint
    """
    guarantor_list = serializers.ListField(child=serializers.CharField(),min_length=0)

    class Meta():
        fields=['guarantor_list']

class AllowedGurantorSerializer(serializers.Serializer):

    """
    Serializer for allowed guarantor display endpoint
    """
    allowed_guarantor_requests = serializers.SerializerMethodField()
    disallowed_guarantor_requests = serializers.SerializerMethodField()

    class Meta():
        fields = ['allowed_guarantor_requests','disallowed_guarantor_requests']

    def get_allowed_guarantor_requests(self,circle_member):
        try:
            members_ids = CircleMember.objects.filter(id__in=AllowedGuarantorRequest.objects.filter(circle_member=circle_member).values_list('allows_request_from',flat=True)).values_list('member',flat=True)
            members = Member.objects.filter(id__in=members_ids).select_related('user')
            serializer = MemberSerializer(members,many=True,context={"request":self.context.get('request')})
            return serializer.data
        except Exception,e:
            print(str(e))
    def get_disallowed_guarantor_requests(self,circle_member):
        try:
            members_ids = CircleMember.objects.filter(Q(circle=circle_member.circle), ~Q(id=circle_member.id)).exclude(id__in=AllowedGuarantorRequest.objects.filter(circle_member=circle_member).values_list('allows_request_from',flat=True)).values_list('member',flat=True)
            members = Member.objects.filter(id__in=members_ids).select_related('user')
            serializer = MemberSerializer(members,many=True,context={"request":self.context.get('request')})
            return serializer.data
        except Exception,e:
            print str(e)

class TokenSerializer(serializers.Serializer):
    """
    Serializer for token endpoint
    """
    token = serializers.CharField()

    class Meta:
        fields = ['token']

class JoinCircleSerializer(serializers.Serializer):
    """
    Serializer for join circle endpoint
    """
    amount = serializers.CharField()
    pin = serializers.CharField()
    circle_acc_number = serializers.CharField()

    class Meta:
        field = ['amount','pin','circle_acc_number']

class CircleMemberSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    surname = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    # passport_url = serializers.ImageField(source='iprs_image')
    # date_of_birth = serializers.SerializerMethodField()
    time_registered = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()
    available_shares = serializers.SerializerMethodField()
    allow_guarantor_request = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ['first_name','surname','other_name','email','gender','country','phone_number','national_id','currency','date_of_birth','time_registered','is_self','available_shares','allow_guarantor_request']


    def get_time_registered(self,member):
         date = member.time_registered
         return date.strftime("%Y-%m-%d %H:%M:%S")

    def get_is_self(self,member):
        request = self.context.get('request')
        is_self = True if request.user.member.national_id == member.national_id else False
        return is_self

    def get_available_shares(self,member):
        circle = self.context.get('circle')
        circle_member = CircleMember.objects.get(member=member,circle=circle)
        total_shares = circle_member.shares.get().num_of_shares
        locked_shares = self.calculate_locked_shares(circle_member.shares.get())
        return total_shares-locked_shares

    def calculate_locked_shares(self,share):
        locked_shares = LockedShares.objects.filter(shares=share)
        if locked_shares.exists():
            locked_shares = locked_shares.aggregate(total=Sum('num_of_shares'))
            return float(locked_shares['total'])
        return 0.0

    def get_allow_guarantor_request(self,member):
        request,circle = self.context.get('request'),self.context.get('circle')
        try:
            user = CircleMember.objects.get(member=request.user.member,circle=circle)
        except CircleMember.DoesNotExist:
            return False
        circle_member = CircleMember.objects.get(member=member,circle=circle)
        if AllowedGuarantorRequest.objects.filter(circle_member=circle_member).exists():
            try:
                AllowedGuarantorRequest.objects.get(circle_member=circle_member,allows_request_from=user)
                return True
            except AllowedGuarantorRequest.DoesNotExist():
                return False
        return True
