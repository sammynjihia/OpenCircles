from .models import Member
from rest_framework import serializers

class MemberSerializer(serializers.ModelSerializer):
    """
    Serializer for member listing endpoint
    """
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.CharField(source='user.email')

    class Meta:
        model = Member
        fields = ['first_name','last_name','email','gender','nationality','phone_number']
