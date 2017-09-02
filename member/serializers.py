from .models import Member
from django.contrib.auth.models import User
from django.utils.timezone import utc

from rest_framework import serializers
from rest_framework.validators import UniqueValidator


class MemberSerializer(serializers.ModelSerializer):
    """
    Serializer for member listing endpoint
    """
    first_name = serializers.CharField(source='user.first_name')
    surname = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    # passport_url = serializers.ImageField(source='iprs_image')
    # date_of_birth = serializers.SerializerMethodField()
    time_registered = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ['first_name','surname','other_name','email','gender','country','phone_number','national_id','currency','date_of_birth','time_registered']



    def get_time_registered(self,member):
         date = member.time_registered
         return date.strftime("%Y-%m-%d %H:%M:%S")
