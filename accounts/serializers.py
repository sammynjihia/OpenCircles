from rest_framework import serializers
from member.models import Member
from django.contrib.auth.models import User


class MemberSerializer(serializers.ModelSerializer):
    """
    Serializer for member registration endpoint
    """
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    password = serializers.CharField(source='user.password',style ={'input_type':'password'},write_only=True)

    class Meta:
        model = Member
        fields = ['first_name','last_name','email','password','national_id','phone_number']

    def create(self,validated_data):
        user_data = validated_data.pop('user')
        username = user_data.get('email')
        user = User.objects.create_user(username = username,**user_data)
        member = Member.objects.create(user=user,**validated_data)
        return member

class PhoneNumberSerializer(serializers.ModelSerializer):
    """
    Serializer for phone number confirmation endpoint
    """
    class Meta:
        model = Member
        fields = ['phone_number']

class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for change password endpoint
    """
    old_password = serializers.CharField()
    new_password = serializers.CharField()

class AuthenticateUserSerializer(serializers.Serializer):
    """
    Serializer for  user login endpoint
    """
    username = serializers.CharField()
    password = serializers.CharField()
