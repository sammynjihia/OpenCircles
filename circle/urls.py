from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^$',api_root,name="api_root"),
    url(r'^circle_create/$',CircleCreation.as_view(),name='circle-create'),
    url(r'^circle_list/$',CircleList.as_view(),name='circle-list'),
    url(r'^circle_list/(?P<pk>[0-9]+)/$',CircleList.as_view(),name='circle-list'),
    url(r'^circle_invitation_response/$',CircleInvitationResponse.as_view(),name='circle-invitation-response')
]
