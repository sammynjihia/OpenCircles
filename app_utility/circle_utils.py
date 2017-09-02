from member.models import Member
from circle.models import Circle as CircleModel,CircleMember,CircleInvitation

import operator

class Circle():
    def get_suggested_circles(self,unjoined_circles,contacts):
        suggested_circles={}
        unjoined_circles = unjoined_circles.filter(circle_type="OPEN")
        for circle in unjoined_circles:
            circle_count = CircleMember.objects.filter(circle=circle,member_id__in=Member.objects.filter(phone_number__in=contacts).values_list('id',flat=True)).count
            suggested_circles[circle]=circle_count
        suggested_circles = sorted(suggested_circles.items(),key=operator.itemgetter(1),reverse=True)[0:5]
        return suggested_circles

    def check_update_circle_status(self,circle):
        if not circle.is_active:
            if CircleMember.objects.filter(circle=circle).count() >= 5:
                circle.update(is_active=True)
        return

    def get_invited_circles(self,request,unjoined_circles):
        circle_members = CircleInvitation.objects.filter(phone_number=request.user.member.phone_number).values_list("invited_by",flat=True)
        circles_ids = CircleMember.objects.filter(id__in=circle_members).values_list('circle',flat=True)
        circles = CircleModel.objects.filter(id__in = circles_ids).order_by('id').distinct('id')
        invited_circles = [circle for circle in circles if circle in unjoined_circles]
        return invited_circles
