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
        m_hash = base64.b64encode(m.digest())
        m_hash = m_hash.translate(None,'/=+')
        return m_hash

    def generate_unique_identifier(self,prefix):
        # random_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
        random_string = self.obfuscate(str(time.time())).upper()[:8]
        code = prefix + random_string
        return code

    def get_decimal(self,nume,deno):
        whole = int(nume/deno)
        res = ""
        whole = str(whole) +"."
        rem = nume%deno
        rem_list = []
        while rem != 0:
            if len(res) == 4:
                break
            rem_list.append(rem)
            rem = rem * 10
            resp_part = int(rem/deno)
            res += str(resp_part)
            rem = rem%deno
            
        dec = whole + res
        dec = float(dec)
        return dec
