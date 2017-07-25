from rest_framework import serializers
from circle.models import Circle

class CircleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Circle
        fields = ('circle_name', 'circle_type')

    def create(self, validated_data):
        return Circle.objects.create(**validated_data)


class CircleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Circle
        fields = ('circle_name', 'circle_type', 'circle_acc_number', 'is_active', 'annual_interest_rate')
