import cherrypy
import logging
from models import User, Client
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


def get_user():
    db = DB(SERVER, PORT)
    if cherrypy.request.login in db.dbroot:
        user = db.dbroot[cherrypy.request.login]
        db.close()
    
        return user

    return None


def create_auth_code(client_id):
    client = get_client(client_id)
    user = get_user()
    db = DB(SERVER, PORT)
    auth_code = AuthCode(client, user)
    db.dbroot[auth_code.code] = auth_code
    transaction.commit()
    db.close()
    
    return auth_code.code


def validate_auth_code(client_id, client_secret, code):
    db = DB(SERVER, PORT)
    if code in db.dbroot:
        auth_code = db.dbroot[code]
        db.close()
        
        user = get_user()
        if auth_code.expire > time() and \
               auth_code.client.id == client_id and \
               auth_code.client.secret == client_secret and \
               auth_code.user.id = user.id:
            
            return True

    return False
