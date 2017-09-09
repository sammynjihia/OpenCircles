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
