from django.shortcuts import render
from rest_framework.views import APIView
from circle.models import Circle
from circle.serializers import CircleCreateSerializer, CircleSerializer
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view
from rest_framework import status
from circle.models import Circle
# Create your views here.
@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'circlecreate': reverse('circlecreate', request=request, format=format),
        'circlelist': reverse('circlelist', request=request, format=format)

    })


class CircleCreation(APIView):
    """
    Creates a circle
    """
    permission_classes = (IsAuthenticated,)
    def post(self, request, *args, **kwargs):
        serializer = CircleCreateSerializer(data=request.data)
        if serializer.is_valid():
            circles = Circle.objects.count()
            if circles == None:
                acc_number = str(2017)
            else:
                acc_number = str(2017 + circles)
            serializer.save(initiated_by=request.user.member, circle_acc_number=acc_number)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CircleList(APIView):
    """
    Lists all the created circles
    """
    def get_object(self,pk):
        try:
            return Circle.objects.get(pk=pk)
        except Circle.DoesNotExist:
            raise status.HTTP_404_NOT_FOUND

    def get(self, request, *args, **kwargs):
        if len(kwargs)>0:
            pk = kwargs.get('pk')
            serializer = CircleSerializer(self.get_object(pk))
        else:
            circles = Circle.objects.all()
            serializer = CircleSerializer(circles, many=True)
        return Response(serializer.data)








