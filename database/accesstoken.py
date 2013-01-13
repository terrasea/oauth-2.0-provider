from DB import DB
from client import get_client
from user import get_user
from models import AccessToken
from tokens import delete_token, get_token

from time import time
from copy import deepcopy
import transaction
import logging


class AccessTokenDB(TokenDB):
    def __init__(self, server=None, port=None, connection=None):
        super(AccessTokenDB, self).__init__('AccessToken', server, port, connection)
        self._client_db = ClientDB(connection=self.connection)
        self._user_db = UserDB(connection=self.connection)
        
        
    def create_from_code(self, auth_code):
        client = self._client_db.get(auth_code.client)
        user = self._user_db.get(auth_code.user)

        try:
            token = AccessToken(client.id,
                                user.id,
                                scope=auth_code.scope)
            while self.contains(token.code):
                token = AccessToken(client.id,
                                    user.id,
                                    scope=auth_code.scope)
            self.put(token.code, token)
            
            return token.code
        except Exception, e:
            logging.error(''.join(['create_access_token_from_code: ', str(e)]))
            raise e
        
        return False


    def create_implicit_grant(self, 
                              uid,
                              client_id,
                              redirect_uri,
                              scope=None):
        user = self._user_db.get(uid)
        client = self._client_db.get(client_id)
        try:
            #the only authentication here is to check the
            #redirect_uri is the same as the one stored
            #for the registered client
            if client.redirect_uri == redirect_uri:
                token = AccessToken(client.id,
                                    user.id,
                                    scope=scope)
                while self.contains(token.code):
                    token = AccessToken(client.id,
                                        user.id,
                                        scope=scope)
                self.put(token.code, token)
                
                return token.code
            else:
                error_str = str(client_id) + ' uri of ' + 
                                str(client.redirect_uri) +
                                ' does not match ' +
                                str(redirect_uri)
                                
                logging.warn(error_str)
                
                raise AuthenticationError(error_str)
                
        except Exception, e:
            logging.error('create_implicit_grant_access_token: ' + str(e))
            
            raise e
        
        return False



    def create_from_user_pass(self, 
                              client_id,
                              client_secret,
                              user_id,
                              password,
                              scope=None):
        client = None
        if client_id != None:
            client = self._client_db.get(client_id)
        else:
            #create a client object from username and password
            client = Client(user_id, user_id, password, None)
            #make client_secret equal the password
            #saving me from having to change anything below
            client_secret = password
        
        user = self._user_db.get(uid)
        
        try:
            if client != None and \
                   user != None and \
                   client.secret == client_secret and \
                   user.password == password:
                token = AccessToken(client.id,
                                    user.id,
                                    scope=scope)
                while self.contains(token.code):
                    token = AccessToken(client.id,
                                        user.id,
                                        scope=scope)

                self.put(token.code, token)


                return token.code
        except Exception, e:
            logging.error('create_access_token_from_user_pass: ' + str(e))
            raise e

        return False



    def create_from_refresh_token(self, refresh_token):
        '''
        We assume that in the getting of the refresh_token,
        before calling this function, the authentication takes place there.
        '''
        
        try:
            #delete old access_token and create a new access_token
            #to replace the old one. refresh_token.access_token is
            #the string code not an AccessToken object
            delete_token(refresh_token.access_token)
            
            #use the info stored in the refresh_token copy to create a
            #new AccessToken
            token = AccessToken(refresh_token.client,
                                refresh_token.user,
                                refresh_token.scope)
            while self.contains(token.code):
                token = AccessToken(refresh_token.client,
                                    refresh_token.user,
                                    refresh_token.scope)

            
            self.put(token.code, token)
            refresh_token.access_token = token.code
            self.update(refresh_token.code, refresh_token)

            #return access token string not AccessToken object
            return token.code
        except Exception, e:
            logging.error('create_access_token_from_refresh_token: ' + str(e))
            raise e


        return False


    def get(self, token_str):
        try:
            if self.contains(token_str):
                token = self.get(token_str)
                
                if isinstance(token, AccessToken) and \
                       not token.expire or \
                       token.expire + token.created > time():
                    return token
                else:
                    error_str = 'get_access_token: Token ' + str(token.code) +
                                 ' has expired for client ' +
                                 str(token.client.id) + ' and user ' +
                                 str(token.user.id)
                    logging.error(error_str)
                    
                    raise ExpireError(error_str)
            else:
                error_str = 'get_access_token: token ' +
                             str(token_str) + ' is not in database'
                logging.error(error_str)
                raise KeyError(error_str)
        except Exception, e:
            logging.error(['get_access_token(' + str(token_str) + '): ' + 
                           str(e))
            raise e 
                           
        return False
        
