from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^create_circle/$', CircleCreation.as_view(), name='circle-create'),
    url(r'^circles_list/$', MemberCircle.as_view(), name='circle-list'),
    url(r'^decline_circle_invitation/$', CircleInvitationResponse.as_view(), name='decline-circle-invitation'),
    url(r'^circle_invite/$', CircleInvite.as_view(), name='circle-invite'),
    url(r'^add_guarantee/$'
    , AllowedGuaranteeRegistration.as_view(), name='add-guarantee'),
    url(r'^set_allowed_guarantee/$'
    ,AllowedGuaranteeRequestsSetting.as_view(), name='set-allowed-guarantor'),
    url(r'^remove_guarantee/$'
    ,remove_allowed_guarantee_request, name='remove-guarantee'),
    url(r'^join_circle/$', JoinCircle.as_view(), name='join-circle'),
    url(r'^get_circle_member_details/$', CircleMemberDetails.as_view(), name='circle-member-details'),
    url(r'^get_allowed_guarantee_requests/$', CircleMemberGuaranteeList.as_view(), name='allowed-guarantee-requests'),
    url(r'^circle_name_verification/$', check_circle_name, name='circle_name_verification'),
    url(r'^get_circle_members/$', get_circle_members, name='get_circle_members')

]
