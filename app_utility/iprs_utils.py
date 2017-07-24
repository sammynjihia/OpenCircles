from zeep import Client
import json

class Iprs():
    def get_person_details(self,national_id):
        client = Client('http://197.155.64.197/Directline/Server.php?wsdl')
        person_data = client.service.handleRequest('ID_NUMBER', national_id)
        return json.loads(person_data)
