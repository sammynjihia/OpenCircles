from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^$',api_root,name="api_root"),
    url(r'^create_circle/$',CircleCreation.as_view(),name='circle-create'),
    url(r'^circles_list/$',MemberCircle.as_view(),name='circle-list'),
    # url(r'^circle_list/(?P<pk>[0-9]+)/$',CircleList.as_view(),name='circle-list'),
    url(r'^circle_invitation_response/$',CircleInvitationResponse.as_view(),name='circle-invitation-response'),
    url(r'^circle_invite/$',CircleInvite.as_view(),name='circle-invite'),
    url(r'^add_guarantee/$'
    ,AllowedGuaranteeRegistration.as_view(),name='add-guarantee'),
    url(r'^set_allowed_guarantee/$'
    ,AllowedGuaranteeRequestsSetting.as_view(),name='set-allowed-guarantor'),
    url(r'^remove_guarantee/$'
    ,remove_allowed_guarantee_request,name='remove-guarantee'),
    url(r'^allowed_guarantor_request_setting/(?P<circlename>[\w]+)/delete/(?P<phonenumber>[\w]+)/$'
    ,delete_objs,name='delete_objs'),
    url(r'^join_circle/$',JoinCircle.as_view(),name='join-circle')
]
