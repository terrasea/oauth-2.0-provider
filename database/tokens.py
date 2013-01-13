from DB import DB
from models import *
from client import get_client

from copy import deepcopy
import logging
import transaction


class TokenDB(DB):
    def __init__(self, collection=None, server=None, port=None, connection=None):
        super(TokenDB, self).__init__(collection, server, port, connection)


    def get(client_id, client_secret, code):
        '''
        This function should get any type of token
        since the code is unique and should only
        return the type of token that was created
        in create_[...]_token
        '''
        try:
            if self.contains(code):
                token = self.get(code)
                client = get_client(token.client)
                if (not token.expire or token.expire + \
                    token.created > time()) and \
                    client.id == client_id and \
                    client.secret == client_secret:
                
                    return token
                else:
                    logging.warn('get_token: Did not authenticate')
            else:
                logging.warn(''.join(['get_token: code ', str(code), ' is not in database']))
        except Exception, e:
            logging.error(''.join(['get_token(',
                                   str(client_id),
                                   ',',
                                   str(client_secret),
                                   ',',
                                   str(code),
                                   '): ',
                                   str(e)]))
                                   
            raise e;
            

        return False



