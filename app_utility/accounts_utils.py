from member.models import Contacts,Member
from app_utility import sms_utils

class Account():
    def check_membership_status(self, param):
        try:
            Member.objects.get(phone_number=param)
            return True
        except Member.DoesNotExist:
            return False

    def save_contacts(self, user, contacts):
        user_contact = Contacts.objects.filter(phone_number=user.phone_number)
        if user_contact.exists():
            user_contact.update(is_member=True)
        if len(contacts):
            instance = sms_utils.Sms()
            contacts = map(dict, set(tuple(self.format_contacts(contact,instance).items()) for contact in contacts))
            for contact in contacts:
                obj = Contacts.objects.filter(phone_number=contact['phone'], member=user)
                if not obj.exists():
                     is_invited = Contacts.objects.filter(phone_number=contact['phone'], invitation_sent=True).exists()
                     Contacts.objects.get_or_create(name=contact['name'], phone_number=contact['phone'], member=user,
                                                    is_member =self.check_membership_status(contact['phone']),
                                                    is_valid=contact['is_valid'], invitation_sent=is_invited)

    def format_contacts(self, contact, instance):
        if len(contact['phone'])>=10:
            rep_chars = [" ","(",")","-"]
            for rep in rep_chars:
                if rep in contact['phone']:
                    contact['phone'] = contact['phone'].replace(rep,"")
            if contact['phone'][0:4] == "+254" or contact['phone'][0:2] == "07":
                contact['phone'] = instance.format_phone_number(contact['phone'])
                contact['is_valid'] = True
            else:
                contact['is_valid'] = False
        else:
            rep_chars = [" ","(",")","-"]
            for rep in rep_chars:
                if rep in contact['phone']:
                    contact['phone'] = contact['phone'].replace(rep,"")
            contact['is_valid'] = False
        return contact
