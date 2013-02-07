from DB import DB
from client import get_client
from user import get_user
from models import AccessToken
from tokens import delete_token, get_token

from time import time
from copy import deepcopy
#import transaction
import logging

def create_access_token_from_code(auth_code):
    client = get_client(auth_code.client)
    user = get_user(auth_code.user)

    db = DB()
    try:
        token = AccessToken(client.id,
                            user.id,
                            scope=auth_code.scope)
        while db.contains(token.code):
            token = AccessToken(client.id,
                                user.id,
                                scope=auth_code.scope)
        db.put(token.code, token)
        
        db.commit()

        return token.code
    except Exception, e:
        logging.error(''.join(['create_access_token_from_code: ', str(e)]))
        db.abort()
    finally:
        db.close()
    
    return False


def create_implicit_grant_access_token(uid, client_id,
                                       redirect_uri, scope=None):
    user = get_user(uid)
    client = get_client(client_id)
    db = DB()
    try:
        
        #the only authentication here is to check the
        #redirect_uri is the same as the one stored
        #for the registered client
        if client.redirect_uri == redirect_uri:
            token = AccessToken(client.id,
                                user.id,
                                scope=scope)
            while db.contains(token.code):
                token = AccessToken(client.id,
                                    user.id,
                                    scope=scope)
            db.put(token.code, token)
            db.commit()
            
            return token.code
        else:
            logging.warn(''.join([str(client_id),
                                  ' uri of ',
                                  str(client.redirect_uri),
                                  ' does not match ',
                                  str(redirect_uri)]))
            
    except Exception, e:
        logging.error(''.join(['create_implicit_grant_access_token: ', str(e)]))
        db.abort()
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
    
    db = DB()
    
    try:
        if client != None and \
               user != None and \
               client.secret == client_secret and \
               user.password == password:
            token = AccessToken(client.id,
                                user.id,
                                scope=scope)
            while db.contains(token.code):
                token = AccessToken(client.id,
                                    user.id,
                                    scope=scope)

            db.put(token.code, token)
            db.commit()



            return token.code
    except Exception, e:
        logging.error(''.join(['create_access_token_from_user_pass: ', 
                               str(e)]))
        db.abort()
    finally:
        db.close()

    return False



def create_access_token_from_refresh_token(refresh_token):
    '''
    We assume that in the getting of the refresh_token,
    before calling this function, the authentication takes place there.
    '''
    
    #disconnect the data reference from the data stored in the DB
    #refresh_token_copy = deepcopy(refresh_token)
    db = DB()
    try:
        #refresh_token = get_token(refresh_token_str)

        #delete old access_token and create a new access_token
        #to replace the old one. refresh_token.access_token is
        #the string code not an AccessToken object
        delete_token(refresh_token.access_token)

    
    
        
        #use the info stored in the refresh_token copy to create a
        #new AccessToken
    
        token = AccessToken(refresh_token.client,
                            refresh_token.user,
                            refresh_token.scope)
        while db.contains(token.code):
            token = AccessToken(refresh_token.client,
                                refresh_token.user,
                                refresh_token.scope)

        
        db.put(token.code, token)
        logging.warn('is a token ' + str(token))
        refresh_token.access_token = token.code
        db.update(refresh_token.code, refresh_token)
        logging.warn('has changed ' + str(refresh_token._p_changed))
        db.commit()

        #return access token string not AccessToken object
        return token.code
    except Exception, e:
        logging.error(''.join(['create_access_token_from_refresh_token: ',
                               str(e)]))
        db.abort()
    finally:
        db.close()

    return False


def get_access_token(token_str):
    db = DB()
    try:
        if db.contains(token_str):
            token = deepcopy(db.get(token_str))
            
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
