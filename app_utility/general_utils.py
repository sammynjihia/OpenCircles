class General():
    def delete_sessions(self,request,keys):
        if type(keys) is not list:
            keys = [keys]
        for key in keys:
            del request.session[key]
