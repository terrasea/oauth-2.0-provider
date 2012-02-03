from DB import ZODB as DB, SERVER, PORT
from models import *

from copy import deepcopy
import logging
import transaction


def get_token(client_id, client_secret, code):
    '''
    This function should get any type of token
    since the code is unique and should only
    return the type of token that was created
    in create_[...]_token
    '''
    db = DB(SERVER, PORT)
    try:
        if code in db.dbroot:
            token = deepcopy(db.dbroot[code])
        
            if (not token.expire or token.expire + \
                token.created > time()) and \
                token.client.id == client_id and \
                token.client.secret == client_secret:
            
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



def get_access_token(token_str):
    db = DB(SERVER, PORT)
    try:
        if token_str in db.dbroot:
            token = deepcopy(db.dbroot[token_str])
            
            if isinstance(token, AccessToken) and \
                   not token.expire or \
                   token.expire + token.created > time():
                return token
            else:
                logging.warn(''.join(['get_access_token: Token ',
                                      str(token.code),
                                      ' has expired for client ',
                                      str(token.client.id),
                                      ' and user ',
                                      str(token.user.id)]))
        else:
            logging.warn(''.join(['get_access_token: token ',
                                  str(token_str),
                                  ' is not in database']))
    except Exception, e:
        logging.error(''.join(['get_access_token(', str(token_str), '): ', str(e)]))
    finally:
        db.close()
            
    return False


def delete_token(token):
    db = DB(SERVER, PORT)
    try:
        if isinstance(token, AuthCode):
            del db.dbroot[token.code]
        elif isinstance(token, str):
            del db.dbroot[token]
        else:
            logging.warning('delete_token: token ' + str(token) + \
                            ' is neither an' + \
                            ' AutCode type nor is it a string')
            return
        
        transaction.commit()
    except Exception, e:
        logging.error('delete_token: ' + str(e))
        transaction.abort()
    finally:
        db.close()

