from DB import DB
from models import *
from client import get_client

from copy import deepcopy
import logging
#import transaction


def get_token(client_id, client_secret, code):
    '''
    This function should get any type of token
    since the code is unique and should only
    return the type of token that was created
    in create_[...]_token
    '''
    db = DB()
    try:
        if db.contains(code):
            token = db.get(code)
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
    finally:
        db.close()

    return False



def delete_token(token):
    db = DB()
    try:
        if isinstance(token, Code):
            db.delete(token.code)
        elif isinstance(token, str):
            db.delete(token)
        else:
            logging.warn('delete_token: token ' + str(token) + \
                            ' is neither an' + \
                            ' AuthCode type nor is it a string')
            return
        
        db.commit()
    except Exception, e:
        logging.error('delete_token: ' + str(e))
        db.abort()
    finally:
        db.close()

