import cherrypy
import logging
from models import User, Client, \
     AuthCode, AccessToken, RefreshToken
from ZEO.ClientStorage import ClientStorage
from ZODB import DB as ZDB
import transaction
from time import time
from copy import deepcopy


SERVER = 'localhost'
PORT = 8000


class DB(object):
    def __init__(self, server, port):
        self.storage = ClientStorage((server, port,))
        #print dir(self.storage)
        self.db = ZDB(self.storage)
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
    return client




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
            
            return deepcopy(client)
    except Exception, e:
        logging.error('get_client' + str(e))
    finally:
        db.close()
    
    return None


def available_scope():
    return tuple()


def get_password(username):
    db = DB(SERVER, PORT)
    if username in db.dbroot:
        try:
            user = db.dbroot[username]
        
            return user.password
        finally:
            db.close()

    return None


def get_user(uid=None):
    db = DB(SERVER, PORT)
    if uid is not None:
        try:
            user = db.dbroot[uid]
        

            return deepcopy(user)
        finally:
            db.close()
    elif cherrypy.request.login in db.dbroot:
        try:
            user = db.dbroot[cherrypy.request.login]
    
            return deepcopy(user)
        finally:
            db.close()

    return None


def create_auth_code(client_id, scope=None):
    try:
        client = get_client(client_id)
        user = get_user()
        db = DB(SERVER, PORT)
        auth_code = AuthCode(client, user, scope=scope)
        db.dbroot[auth_code.code] = auth_code
        transaction.commit()
        code = deepcopy(auth_code.code)
        db.close()
        return code
    finally:
        db.close()



def get_auth_code(client_id, client_secret, code):
    db = DB(SERVER, PORT)
    if code in db.dbroot:
        auth_code = deepcopy(db.dbroot[code])
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
    delete_token(refresh_token.access_token)
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
        token = deepcopy(db.dbroot[code])
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
    


if __name__ == '__main__':
    from mock import patch
    from unittest import TestCase, main
    from ZODB.FileStorage import FileStorage

    class ClientStorage(FileStorage):
        def __init__(self, server_port):
            super(ClientStorage, self).__init__('/tmp/testdb.fs')
            

    
    
    class TestDBFunctions(TestCase):
        client_name = 'joe joe'
        client_id = 'client_id'
        client_secret = 'secret'
        redirect_uri = 'localhost'
        client_type = 'type'
        user_id = 'user'
        user_password = 'password'
        
        def setUp(self):
            db = DB(SERVER, PORT)
            db.dbroot.clear()
            transaction.commit()
            db.close()
                
        
        def test_create_client(self):
            
            client = create_client(TestDBFunctions.client_name,
                                   TestDBFunctions.client_id,
                                   TestDBFunctions.client_secret,
                                   TestDBFunctions.redirect_uri,
                                   TestDBFunctions.client_type)
            db = DB(SERVER, PORT)
            self.assertEqual(db.dbroot[TestDBFunctions.client_id].id, client.id)
            db.close()
            
            

        def test_client_exists_function(self):
            client = Client(TestDBFunctions.client_name,
                            TestDBFunctions.client_id,
                            TestDBFunctions.client_secret,
                            TestDBFunctions.redirect_uri,
                            TestDBFunctions.client_type)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.client_id] = client
            transaction.commit()
            db.close()

            self.assertTrue(client_exists(TestDBFunctions.client_id))


        def test_get_client(self):
            client = Client(TestDBFunctions.client_name,
                            TestDBFunctions.client_id,
                            TestDBFunctions.client_secret,
                            TestDBFunctions.redirect_uri,
                            TestDBFunctions.client_type)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.client_id] = client
            transaction.commit()
            db.close()

            client2 = get_client(TestDBFunctions.client_id)
            self.assertEqual(client2.id, client.id)


        def test_get_password(self):
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            transaction.commit()
            db.close()

            password = get_password(TestDBFunctions.user_id)
            self.assertEqual(password, TestDBFunctions.user_password)


        def test_get_user_by_uid(self):
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            transaction.commit()
            db.close()

            user2 = get_user(TestDBFunctions.user_id)
            self.assertEqual(user2.id, TestDBFunctions.user_id)

        def test_get_user(self):
            cherrypy.request.login = TestDBFunctions.user_id
            
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            transaction.commit()
            db.close()
            
            user2 = get_user()
            self.assertEqual(user2.id, TestDBFunctions.user_id)


        def test_create_auth_code(self):
            client = Client(TestDBFunctions.client_name,
                            TestDBFunctions.client_id,
                            TestDBFunctions.client_secret,
                            TestDBFunctions.redirect_uri,
                            TestDBFunctions.client_type)
            cherrypy.request.login = TestDBFunctions.user_id
            
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            db.dbroot[TestDBFunctions.client_id] = client
            transaction.commit()
            db.close()
            

            code = create_auth_code(TestDBFunctions.client_id)
            self.assertIsNotNone(code)
            db = DB(SERVER, PORT)
            self.assertTrue(code in db.dbroot)
            self.assertTrue(isinstance(code, str))
            code2 = deepcopy(db.dbroot[code])
            db.close()

            self.assertEqual(code, code2.code)

            
           
            

    
    main()
    
    
