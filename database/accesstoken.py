from DB import DB, SERVER, PORT
from client import get_client
from user import get_user
from models import AccessToken

from copy import deepcopy
import transaction


def create_access_token_from_code(auth_code):
    client = get_client(auth_code.client.id)
    user = get_user(auth_code.user.id)

    db = DB(SERVER, PORT)
    try:
        token = AccessToken(client,
                            user,
                            scope=auth_code.scope)
        db.dbroot[token.code] = token
        transaction.commit()

        return token.code
    except Exception, e:
        logging.error(''.join(['create_access_token_from_code: ', str(e)]))
        transaction.abort()
    finally:
        db.close()
    
    return False


def create_implicit_grant_access_token(uid, client_id,
                                       redirect_uri, scope=None):
    user = get_user(uid)
    client = get_client(client_id)
    db = DB(SERVER, PORT)
    try:
        
        #the only authentication here is to check the
        #redirect_uri is the same as the one stored
        #for the registered client
        if client.redirect_uri == redirect_uri:
            token = AccessToken(client,
                                user,
                                scope=scope)
            db.dbroot[token.code] = token
            transaction.commit()
            
            return token.code
        else:
            logging.warn(''.join([str(client_id),
                                  ' uri of ',
                                  str(client.redirect_uri),
                                  ' does not match ',
                                  str(redirect_uri)]))
            
    except Exception, e:
        logging.error(''.join(['create_implicit_grant_access_token: ', str(e)]))
        transaction.abort()
    finally:
        db.close()
    
    return False



def create_access_token_from_user_pass(client_id,
                                       client_secret,
                                       user_id,
                                       password,
                                       scope):
    client = None
    if client_id != None:
        client = get_client(client_id)
    else:
        #create a client object from username and password
        client = Client(user_id, user_id, password, None)
        #make client_secret equal the password
        #saving me from having to change anything below
        client_secret = password
        
    user = get_user(user_id)
    
    db = DB(SERVER, PORT)
    
    try:
        if client != None and \
               user != None and \
               client.secret == client_secret and \
               user.password == password:
            token = AccessToken(client,
                                user,
                                scope=scope)


            db.dbroot[token.code] = token
            transaction.commit()



            return token.code
    except Exception, e:
        logging.error(''.join(['create_access_token_from_user_pass: ', 
                               str(e)]))
        transaction.abort()
    finally:
        db.close()

    return False



def create_access_token_from_refresh_token(refresh_token):
    '''
    We assume that in the getting of the refresh_token,
    before calling this function, the authentication takes place there.
    '''
    #disconnect the data reference from the data stored in the DB
    refresh_token_copy = deepcopy(refresh_token)

    #use the info stored in the refresh_token copy to create a
    #new AccessToken
    token = AccessToken(refresh_token_copy.client,
                        refresh_token_copy.user,
                        refresh_token_copy.scope)
    if token == None:
        return False
    #delete old access_token and create a new access_token
    #to replace the old one. refresh_token.access_token is
    #the string code not an AccessToken object
    delete_token(refresh_token_copy.access_token)
    
    db = DB(SERVER, PORT)

    try:
        db.dbroot[token.code] = token
        refresh_token.access_token = token
        refresh_token._p_changed = True
        transaction.commit()

        #return access token string not AccessToken object
        return token.code
    except Exception, e:
        logging.error(''.join(['create_access_token_from_refresh_token: ',
                               str(e)]))
        transaction.abort()
    finally:
        db.close()

    return False
