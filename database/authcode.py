from DB import ZODB as DB, SERVER, PORT
from user import get_user
from client import get_client
from models import AuthCode


import transaction
import logging
from copy import deepcopy
from time import time

def create_auth_code(client_id, uid, scope=None):
    client = get_client(client_id)
    user = get_user(uid)
    db = DB(SERVER, PORT)
    try:
        auth_code = AuthCode(client, user, scope=scope)
        db.dbroot[auth_code.code] = auth_code
        transaction.commit()
        code = deepcopy(auth_code.code)
        logging.warn('create_auth_code: ' + str(code))
        return code
    except Exception, e:
        logging.error(''.join(['create_auth_code: ', str(e)]))
        transaction.abort()
    finally:
        #transaction.commit()
        db.close()

    return None



def delete_auth_code(code):
    db = DB(SERVER, PORT)
    try:
        if code in db.dbroot:
            del db.dbroot[code]
            transaction.commit()
    except Exception, e:
        logging.error('delete_auth_code: ' + str(e))
        tranaction.abort()

        return False
    finally:
        db.close()

    return True
    



def get_auth_code(client_id, client_secret, code):
    db = DB(SERVER, PORT)
    try:
        if code in db.dbroot:
            auth_code = deepcopy(db.dbroot[code])
                
            if auth_code.expire + auth_code.created > time() and \
                   auth_code.client.id == client_id and \
                   auth_code.client.secret == client_secret:
                return auth_code
    except Exception, e:
        logging.error(''.join(['get_auth_code: ', str(e)]))
    finally:
        db.close()


    return False
