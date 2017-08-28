from member.models import Contacts,Member

class Account():
    def check_membership_status(self,param):
        try:
            member=Member.objects.get(phone_number=param)
            return True
        except Member.DoesNotExist:
            return False

    def save_contacts(self,user,contacts):
        user_contact = Contacts.objects.filter(phone_number=user.phone_number)
        if user_contact.exists():
            user_contact.update(is_member=True)
        if len(contacts):
            try:
                contacts_objs = [Contacts(name=contact['name'],phone_number=contact['phone'],member=user,is_member =self.check_membership_status(contact['phone'])) for contact in contacts]
                Contacts.objects.bulk_create(contacts_objs)
            except Exception,e:
                print str(e)
