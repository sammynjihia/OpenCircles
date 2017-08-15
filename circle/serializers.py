from rest_framework import serializers
from .models import Circle,CircleMember
from member.serializers import MemberSerializer
from member.models import Member

class CircleCreationSerializer(serializers.ModelSerializer):
    """
    Serializer for circle registration endpoint
    """
    contact_list = serializers.ListField(child=serializers.CharField(),min_length=0,write_only=True)
    class Meta:
        model = Circle
        fields = ['circle_name','circle_type','contact_list']

    def create(self,validated_data):
        validated_data.pop('contact_list')
        return Circle.objects.create(**validated_data)

class CircleSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for circle listing endpoint
    """
    initiated_by = serializers.HyperlinkedRelatedField(view_name='member-detail',read_only=True)
    member_count = serializers.SerializerMethodField()
    date_created = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()

    class Meta:
        model = Circle
        fields = ['circle_name','circle_type','circle_acc_number','is_active','members','initiated_by','date_created','annual_interest_rate','member_count']

    def get_member_count(self,circle):
        return CircleMember.objects.filter(circle_id=circle.id).count()

    def get_date_created(self,circle):
        return circle.time_initiated.date()

    def get_members(self,circle):
        members_ids = CircleMember.objects.filter(circle_id=circle.id).values_list('member',flat=True)
        members = Member.objects.filter(id__in=members_ids).select_related('user')
        serializer = MemberSerializer(members,many=True,context={"request":self.context.get('request')})
        return serializer.data

class CircleInvitationSerializer(serializers.Serializer):
    """
    Serializer for circle invitation response
    """
    invite_id = serializers.CharField()
    invite_response = serializers.ChoiceField(choices=['A','D'])
