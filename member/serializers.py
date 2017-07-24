from .models import Member
from rest_framework import serializers

class MemberSerializer(serializers.ModelSerializer):
    """
    Serializer for member listing endpoint
    """
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.CharField(source='user.email')
    passport_url = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ['first_name','last_name','email','passport_url','gender','nationality','phone_number']

    def get_passport_url(self, members):
        request = self.context.get('request')
        passport_url = members.passport_image.url
        domain = request.META['HTTP_HOST']
        protocol = 'http'
        url = '{}://{}/{}'.format(protocol,domain,passport_url)
        return url
