from DB import ZODB as DB, SERVER, PORT
from errors import *
from models import Association
from tokens import get_token

import logging
import transaction
from copy import deepcopy


def isassociated(user, client, refresh_token_str):
    db = DB(SERVER, PORT)
    try:
        key = 'client_association_' + str(user.id)
        if db.contains(key):
            association = db.get(key)
            return client.id in association.clients
        else:
            return False
                
    except Exception, e:
        logging.error('isassociated: ' + str(e))
        raise e
    finally:
        db.close()

    return False

def associate_client_with_user(user, client, refresh_token_str):
    """
    Adds client to list of authorised clients who can access the users resources on a long term basis
    """
    refresh_token = get_token(client.id, client.secret, refresh_token_str)
    ## before going further, see if client is confidential or not.
    ## If confidential then it is assumed to be able to keep the
    ## username and password secret from itself.  If this is the
    ## case then it's allowed to continue, else throw a
    ## ConfindentialError.
    if refresh_token.client.type.lower() != 'confidential':
        client_id = refresh_token.client.id
        raise ConfidentailError('Client ' + client_id + \
                                ' is not a confidentail client')
    

    
    db = DB(SERVER, PORT)
    try:
        key = 'client_association_' + str(user.id)
        if db.contains(key):
            association = db.get(key)
            if client.id not in association.clients:
                association.clients[client.id] = refresh_token
                db.update(key, association)
            else:
                raise AssociationExistsWarning(''.join(['Client ',
                                                        str(client.id),
                                                        ' is already associated with ',
                                                        str(user.id)]))
        else:
            association = Association(deepcopy(user))
            association.clients[client.id] = get_token(client.id,
                                                       client.secret,
                                                       refresh_token_str)
            db.put(key, association)
            
        db.commit()
    except Exception, e:
        logging.error(''.join(['associate_client_with_user: ', str(e)]))
        raise e
        db.abort()
    finally:
        db.close()




def get_associations(user):
    db = DB(SERVER, PORT)
    try:
        key = 'client_association_' + str(user.id)
        if db.contains(key):
            return deepcopy(db.get(key))
    except Exception, e:
        logging.error('get_associations: ' + str(e))
    finally:
        db.close()

    return False




def update_association(user, client, refresh_token_str):
    refresh_token = get_token(client.id, client.secret, refresh_token_str)
    #always check to see if it is confidential or not.
    #it shouldn't be if it's using update_association, but you never know
    #and it's good to have a log message to possible alert the admin that
    #this is going on.
    if refresh_token.client.type.lower() != 'confidential':
        client_id = refresh_token.client.id
        raise ConfidentailError('Client ' + client_id + \
                                ' is not a confidentail client')

    db = DB(SERVER, PORT)
    try:
        key = 'client_association_' + str(user.id)
        if db.contains(key):
            association = db.get(key)
            if client.id in association.clients:
                 association.clients[client.id] = refresh_token
                 db.update(key, association)
                 db.commit()
    except Exception, e:
        logging.error('get_associations: ' + str(e))
        db.abort()
    finally:
        db.close()

    return False



if __name__ == '__main__':
    from user import add_user, get_user, delete_user
    from client import create_client, get_client, delete_client
    from models import RefreshToken
    add_user('jim', 'password')
    user = get_user('jim')
    client = create_client('bob',
                           'bobby',
                           'iamcool',
                           'http://whaever.com')
    associate_client_with_user(user, client, '')
