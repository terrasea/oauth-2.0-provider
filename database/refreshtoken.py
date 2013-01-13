from tokens import TokenDB
from models import RefreshToken
from client import ClientDB
from user import UserDB
from authcode import AuthCodeDB

import logging


class RefreshTokenDB(TokenDB):
    def __init__(self, server=None, port=None, connection=None):
        super(RefreshTokenDB, self).__init__('RefreshToken', server, port, connection)
        self._auth_code_db = AuthCodeDB(server, port, self.connection)
        self._client_db = ClientDB(connection=self.connection)
        self._user_db = UserDB(connection=self.connection)


    def create_from_code(self, auth_code, access_token):
        try:
            token = RefreshToken(access_token,
                                 auth_code.client,
                                 auth_code.user,
                                 scope=auth_code.scope)
            while self.contains(token.code):
                token = RefreshToken(access_token,
                                     auth_code.client,
                                     auth_code.user,
                                     scope=auth_code.scope)
            self.put(token.code, token)
            
            return token.code
        except Exception, e:
            logging.error(''.join(['create_refresh_token_from_code ', str(e)]))
            raise e;
        finally:
            self._auth_code_db.delete(auth_code)

        return False


    def create_from_user_pass(self,
                              client_id,
                              client_secret,
                              user_id,
                              password,
                              scope,
                              access_token):
        try:
            client = None
            if client_id != None:
                client = self._client_db.get(client_id)
            else:
                #not using client credentials do just create
                #a client object from user credentials
                client = Client(user_id, user_id, password, None)
                #make client_secret equal password
                client_secret = password
                
            user = self._user_db.get(user_id)
            if client != None and \
                   user != None and \
                   client.secret == client_secret and \
                   user.password == password:
                try:
                    token = RefreshToken(access_token.code,
                                         client.id,
                                         user.id,
                                         scope=scope)
                    while self.contains(token.code):
                        token = RefreshToken(access_token.code,
                                             client.id,
                                             user.id,
                                             scope=scope)
                    self.put(token.code, token)
                    

                    return token.code
                except Exception, e:
                    logging.error(''.join(['create_refresh_token_from_user_pass: ',
                                           str(e)]))
                    raise e
        except Exception, e:
            logging.error(''.join(['create_refresh_token_from_user_pass: ',
                                   str(e)]))
            raise e
        

        return False

