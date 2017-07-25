from django.conf.urls import url
from circle.views import CircleCreation, api_root, CircleList
from rest_framework.urlpatterns import format_suffix_patterns


urlpatterns =[
    url(r'^circlecreate/$', CircleCreation.as_view(), name='circlecreate'),
    url(r'^circlelist/$', CircleList.as_view(), name='circlelist' ),
    url(r'^circlelist/(?P<pk>[0-9]+)$', CircleList.as_view()),
    url(r'^$', api_root, name='api_root')

]

urlpatterns = format_suffix_patterns(urlpatterns)

