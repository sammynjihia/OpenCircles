from .models import Member,Beneficiary
from django.contrib.auth.models import User
from django.core.files import File

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

import base64


class MemberSerializer(serializers.ModelSerializer):
    """
    Serializer for member listing endpoint
    """
    first_name = serializers.CharField(source='user.first_name')
    surname = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    passport_image = serializers.SerializerMethodField()
    time_registered = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ['first_name','surname','other_name','email','gender','country','phone_number','national_id',
                  'currency','date_of_birth','time_registered','passport_image']

    def get_time_registered(self, member):
         date = member.time_registered
         return date.strftime("%Y-%m-%d %H:%M:%S")

    def get_passport_image(self, member):
        if member.passport_image:
            # f = open(member.passport_image.path, 'rb')
            # image = File(f)
            # data = base64.b64encode(image.read())
            # f.close()
            try:
                with open(member.passport_image.path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read())
                with open('image_file.txt', 'w') as post_file:
                    post_file.write(str(encoded_string))
                print(encoded_string)
                return encoded_string
            except Exception as exp:
                return ''
        else:
            return ''

class BeneficiarySerializer(serializers.ModelSerializer):
    """
    Serializer for registering Beneficiary
    """

    other_name = serializers.CharField(source='last_name')
    pin = serializers.CharField(write_only=True)
    email = serializers.EmailField(allow_blank=True)

    def create(self, validated_data):
        validated_data.pop('pin')
        beneficiary = Beneficiary.objects.create(**validated_data)
        return beneficiary

    class Meta:
        model = Beneficiary
        fields = ['first_name','other_name','pin','gender','relationship','phone_number','email','benefit',
                  'date_of_birth']


class MemberBeneficiarySerializer(serializers.ModelSerializer):
    """
    Serializer for registering Beneficiary
    """

    other_name = serializers.CharField(source='last_name')
    benefit = serializers.SerializerMethodField()

    class Meta:
        model = Beneficiary
        fields = ['first_name','other_name','gender','relationship','phone_number','email','benefit','date_of_birth']

    def get_benefit(self, beneficiary):
        return beneficiary.benefit*100

class NewContactSerializer(serializers.Serializer):
    """
    Serializer for new contact endpoint
    """
    contacts = serializers.DictField()
