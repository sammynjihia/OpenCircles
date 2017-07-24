from django.conf.urls import url,include
# from rest_framework.routers import DefaultRouter
from . import views

# router = DefaultRouter()
# router.register(r'members',views.MemberViewSet)

urlpatterns = [
    # url(r'^',include(router.urls)),
    url(r'^$',views.api_root),
    url(r'^member_list/$',views.MemberList.as_view(),name='member-list'),
    url(r'^member_list/(?P<pk>[0-9]+)/$',views.MemberDetail.as_view(),name='member-detail')
]
