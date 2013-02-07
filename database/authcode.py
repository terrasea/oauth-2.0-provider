from DB import DB
from user import get_user
from client import get_client
from models import AuthCode


#import transaction
import logging
from copy import deepcopy
from time import time

def create_auth_code(client_id, uid, scope=None):
    client = get_client(client_id)
    user = get_user(uid)
    db = DB()
    try:
        auth_code = AuthCode(client.id, user.id, scope=scope)
        while db.contains(auth_code.code):
            token = AccessToken(client.id,
                                user.id,
                                scope=scope)
        db.put(auth_code.code, auth_code)
        db.commit()
        code = auth_code.code
        
        return code
    
    except Exception, e:
        logging.error(''.join(['create_auth_code: ', str(e)]))
        db.abort()
        raise e
    finally:
        db.close()

    return None



def delete_auth_code(code):
    db = DB()
    try:
        if db.contains(code):
            db.delete(code)
            db.commit()
    except Exception, e:
        logging.error('delete_auth_code: ' + str(e))
        db.abort()

        return False
    finally:
        db.close()

    return True
    



def get_auth_code(client_id, client_secret, code):
    db = DB()
    try:
        if db.contains(code):
            auth_code = deepcopy(db.get(code))
            client = get_client(auth_code.client)
            if auth_code.expire + auth_code.created > time() and \
                   client.id == client_id and \
                   client.secret == client_secret:
                return auth_code
    except Exception, e:
        logging.error(''.join(['get_auth_code: ', str(e)]))
    finally:
        db.close()


    return False
