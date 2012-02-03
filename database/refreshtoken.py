from DB import DB, SERVER, PORT
from models import RefreshToken
from client import get_client

import transaction
from copy import deepcopy
import logging


def create_refresh_token_from_code(auth_code, access_token):
    db = DB(SERVER, PORT)
    
    try:
        auth_code = deepcopy(auth_code)
        token = RefreshToken(access_token,
                             auth_code.client,
                             auth_code.user,
                             scope=auth_code.scope)
        db.dbroot[token.code] = token
        transaction.commit()
        
        return token.code
    except Exception, e:
        logging.error(''.join(['create_refresh_token_from_code ', str(e)]))
        transaction.abort()
    finally:
        db.close()
        delete_token(auth_code)

    return False


def create_refresh_token_from_user_pass(client_id,
                                        client_secret,
                                        user_id,
                                        password,
                                        scope,
                                        access_token):
    try:
        client = None
        if client_id != None:
            client = get_client(client_id)
        else:
            #not using client credentials do just create
            #a client object from user credentials
            client = Client(user_id, user_id, password, None)
            #make client_secret equal password
            client_secret = password
            
        user = get_user(user_id)
        if client != None and \
               user != None and \
               client.secret == client_secret and \
               user.password == password:
            db = DB(SERVER, PORT)
            try:
                token = RefreshToken(access_token,
                                     client,
                                     user,
                                     scope=scope)
                db.dbroot[token.code] = token
                
                transaction.commit()

                return token.code
            except Exception, e:
                logging.error(''.join(['create_refresh_token_from_user_pass: ',
                                       str(e)]))
                transaction.abort()
            finally:
                db.close()
    except Exception, e:
        logging.error(''.join(['create_refresh_token_from_user_pass: ',
                               str(e)]))
    

    return False
