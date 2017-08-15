from zeep import Client
import json

class Iprs():
    def get_person_details(self,national_id):
        try:
            client = Client('http://197.155.64.197/Directline/Server.php?wsdl')
            person_data = client.service.handleRequest('ID_NUMBER', national_id)
            return json.loads(person_data)
        except Exception,e:
            return false

    def validate_info(self,iprs_info,app_info):
        for key,value in app_info.items():
            if app_info[key] != iprs_info[key]:
                error = {key:["Mismatch"]}
                return False,error
        return True

    def save_extracted_iprs_info(self,new_member,person_data):
        member_info = { new_key : person_data.get(key) for new_key,key in {'nationality':'citizenship','gender':'gender','date_of_birth':'dateOfBirth','passport_image_url':'photoPath'}.items()}
        for key,value in member_info.items():
            if key == "date_of_birth":
                value = datetime.datetime.strptime(value,'%m/%d/%Y %I:%M:%S %p').date()
            elif key == "gender":
                value = value.lower()
                if value == "male":
                    value = "M"
                else:
                    value = "F"
            setattr(new_member, key, value)
        return
