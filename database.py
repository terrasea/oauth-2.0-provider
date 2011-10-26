import cherrypy
import logging
from models import User, Client, \
     AuthCode, AccessToken, RefreshToken
from ZEO.ClientStorage import ClientStorage
from ZODB import DB
import transaction
from time import time



SERVER = 'localhost'
PORT = 8000


class DB(object):
    def __init__(self, server, port):
        self.storage = ClientStorage((server, port,))
        self.db = DB(self.storage)
        self.connection = self.db.open()
        self.dbroot = self.connection.root()

    def close(self):
        self.connection.close()
        self.db.close()
        self.storage.close()



def create_client(client_name,
                  client_id,
                  client_secret,
                  redirect_uri,
                  client_type):
    db = DB(SERVER, PORT)
    client = Client( client_name,
                     client_id,
                     client_secret,
                     redirect_uri,
                     client_type)
    db.dbroot[client_id] = client
    transaction.commit()
    db.close()
    pass




def client_exists(client_id):
    db = DB(SERVER, PORT)
    try:
        if client_id in db.dbroot:
            db.close()
            return True
    except:
        pass
    return False



def get_client(client_id):
    db = DB(SERVER, PORT)
    try:
        if client_id in db.dbroot:
            client = db.dbroot[client_id]
            db.close()
            return client
    except Exception, e:
        logging.error(str(e))
    
    return None


def available_scope():
    return tuple()


def get_password(username):
    db = DB(SERVER, PORT)
    if username in db.dbroot:
        user = db.dbroot[username]
        db.close()
        return user.password

    return None


def get_user(uid=None):
    db = DB(SERVER, PORT)
    if uid not None:
        user = db.dbroot[uid]
        db.close()

        return user
    elif cherrypy.request.login in db.dbroot:
        user = db.dbroot[cherrypy.request.login]
        db.close()
    
        return user

    return None


def create_auth_code(client_id, scope=None):
    client = get_client(client_id)
    user = get_user()
    db = DB(SERVER, PORT)
    auth_code = AuthCode(client, user, scope=scope)
    db.dbroot[auth_code.code] = auth_code
    transaction.commit()
    db.close()
    
    return auth_code.code



def get_auth_code(client_id, client_secret, code):
    db = DB(SERVER, PORT)
    if code in db.dbroot:
        auth_code = db.dbroot[code]
        db.close()
        
        if auth_code.expire > time() and \
               auth_code.client.id == client_id and \
               auth_code.client.secret == client_secret:
            return auth_code
    else:
        db.close()


    return False



def create_access_token_from_code(auth_code):
    db = DB(SERVER, PORT)
    token = AccessToken(auth_code.client,
                        auth_code.user,
                        scope=auth_code.scope)
    db.dbroot[token.code] = token
    transaction.commit()
    db.close()

    return token.code



def create_access_token_from_user_pass(client_id,
                                       client_secret,
                                       user_id,
                                       password,
                                       scope):
    db = DB(SERVER, PORT)
    client = get_client(client_id)
    user = get_user(user_id)
    if client != None and \
           user != None and \
           client.secret == client_secret and \
           user.password == password:
        token = AccessToken(client,
                            user,
                            scope=scope)
        db.dbroot[token.code] = token
        transaction.commit()
        db.close()

        return token.code

    db.close()

    return None



def create_access_token_from_refresh_token(refresh_token):
    '''
    We assume that in getting the refresh_token,
    the authentication takes place there.
    '''
    token = AccessToken(refresh_token.client,
                        refresh_token.user,
                        refresh_token.scope)
    db.dbtoken[token.code] = token
    refresh_token.access_token = token
    refresh_token._p_changed = True
    transaction.commit()
    db.close()

    return token.code



def create_refresh_token_from_code(auth_code, access_token):
    db = DB(SERVER, PORT)
    token = RefreshToken(access_token,
                         auth_code.client,
                         auth_code.user,
                         scope=auth_code.scope)
    db.dbroot[token.code] = token
    transaction.commit()
    db.close()

    return token.code


def create_refresh_token_from_user_pass(client_id,
                                        client_secret,
                                        user_id,
                                        password,
                                        scope,
                                        access_token):
    db = DB(SERVER, PORT)
    client = get_client(client_id)
    user = get_user(user_id)
    if client != None and \
           user != None and \
           client.secret == client_secret and \
           user.password == password:
        token = RefreshToken(access_token,
                             client,
                             user,
                             scope=scope)
        db.dbroot[token.code] = token
        transaction.commit()
        db.close()

        return token.code

    db.close()

    return None


def get_token(client_id, clinet_secret, code):
    '''
    This function should get any type of token
    since the code is unique and should only
    return the type of token that was created
    in create_[...]_token
    '''
    db = DB(SERVER, PORT)
    if code in db.dbroot:
        token = db.dbroot[code]
        db.close()
        
        if token.expire > time() and \
               token.client.id == client_id and \
               token.client.secret == client_secret:
            
            return token

    return False



def delete_token(token):
    db = DB(SERVER, PORT)
    del db.dbroot[token.code]
    transaction.commit()
    db.close()
    
