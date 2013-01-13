from user import UserDB
from client import ClientDB
from tokens import TokenDB
from models import AuthCode



import logging
from time import time

class AuthCodeDB(TokenDB):
    def __init__(self, server=None, port=None, connection=None):
        super(AuthCodeDB, self).__init__('AuthCode', server, port, connection)
        self._client_db = ClientDB(connection=self.connection)
        self._user_db = UserDB(connection=self.connection)


    def create(self, client_id, uid, scope=None):
        client = self._client_db.get(client_id)
        user = self._user_db.get(uid)

        try:
            auth_code = AuthCode(client.id, user.id, scope=scope)
            while self.contains(auth_code.code):
                token = AuthCode(client.id,
                                 user.id,
                                 scope=scope)
            self.put(auth_code.code, auth_code)

            code = auth_code.code
            
            return code
        
        except Exception, e:
            logging.error(''.join(['create_auth_code: ', str(e)]))
            raise e

        return None



    def get(self, client_id, client_secret, code):
        try:
            if self.contains(code):
                auth_code = self.get(code)
                client = self._client_db.get(auth_code.client)
                if auth_code.expire + auth_code.created > time() and \
                       client.id == client_id and \
                       client.secret == client_secret:
                    return auth_code
        except Exception, e:
            logging.error(''.join(['get_auth_code: ', str(e)]))
            raise e

        return False
        
