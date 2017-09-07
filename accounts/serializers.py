from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from member.models import Member
from django.contrib.auth.models import User

from app_utility import sms_utils



class MemberRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for member registration endpoint
    """
    first_name = serializers.CharField(source='user.first_name')
    surname = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    pin = serializers.CharField(source='user.password',style ={'input_type':'password'},write_only=True)
    contact_list = serializers.ListField(child = serializers.ListField(serializers.DictField(child=serializers.CharField())),min_length=0,required=False)
    phone = serializers.CharField(source='phone_number')
    country_name = serializers.CharField(source='country')

    class Meta:
        model = Member
        fields = ['first_name','surname','other_name','gender','date_of_birth','image','email','pin','national_id','phone','country_name','contact_list']

    def create(self,validated_data):
        if 'image' in validated_data:
            validated_data.pop('image')
        user_data = validated_data.pop('user')
        username = sms_utils.Sms().format_phone_number(validated_data.get('phone_number'))
        validated_data['phone_number'] = username
        user = User.objects.create_user(username = username,**user_data)
        member = Member.objects.create(user=user,**validated_data)
        return member

class PhoneNumberSerializer(serializers.ModelSerializer):
    """
    Serializer for phone number confirmation endpoint
    """
    phone = serializers.CharField(source='phone_number')
    class Meta:
        model = Member
        fields = ['phone']

class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for change password endpoint
    """
    old_pin = serializers.CharField()
    new_pin = serializers.CharField()

class AuthenticateUserSerializer(serializers.Serializer):
    """
    Serializer for  user login endpoint
    """
    username = serializers.CharField()
    pin = serializers.IntegerField()
