from member.models import Contacts


class ContactsUtils:
    @staticmethod
    def get_contacts_list():
        contacts = Contacts.objects.all().order_by('name').distinct('phone_number', 'name')
        return contacts


    @staticmethod
    def get_num_of_all_contacts():
        return Contacts.objects.all().distinct('phone_number').count()

    @staticmethod
    def get_num_of_all_non_invited_contact():
        return Contacts.objects.filter(invitation_sent=False).distinct('phone_number').count()

    @staticmethod
    def get_num_of_all_invited_contact():
        contacts = Contacts.objects.filter(invitation_sent=True).distinct('phone_number').count()
        print("Contacts sent ---> {}".format(contacts))
        return contacts
