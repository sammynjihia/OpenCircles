import string,random
import time
import hashlib
import base64

class General():
    def delete_sessions(self,request,keys):
        if type(keys) is not list:
            keys = [keys]
        for key in keys:
            del request.session[key]

    def delete_created_objects(self,created_objects):
        for obj in created_objects:
            if type(obj) is list:
                for ob in obj:
                    ob.delete()
            else:
                obj.delete()

    def obfuscate(self, s):
        m = hashlib.sha256()
        m.update(s)
        hash = base64.b64encode(m.digest())
        return hash

    def generate_unique_identifier(self,prefix):
        # random_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
        random_string = obfuscate(str(time.time())).upper()[:8]
        code = prefix + random_string
        return code
