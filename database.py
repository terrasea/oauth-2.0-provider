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
PORT = 6000


class DB(object):
    def __init__(self, server, port):
        self.storage = ClientStorage((server, port,))
        self.db = ZDB(self.storage)
        self.connection = self.db.open()
        self.dbroot = self.connection.root()

    def close(self):
        self.connection.close()
        self.db.close()
        self.storage.close()



def add_anonymous_url(url):
    try:
        db = DB(SERVER, PORT)
        if 'anonymous_urls' in db.dbroot:
            urls = db.dbroot['anonymous_urls']
            urls.append(url)
            db.dbroot['anonymous_urls'] = urls
        else:
            urls = list()
            urls.append(url)
            db.dbroot['anonymous_urls'] = urls
        transaction.commit()
    except Exception, e:
        logging.error('add_anonymous_url: %s' % (str(e)))
        transaction.abort()
    finally:
        db.close()
        

def get_anonymous_urls():
    try:
        db = DB(SERVER, PORT)
        return db.dbroot['anonymous_urls']
    except Exception, e:
        logging.error('get_anonymous_urls: %s' % (str(e)))
    finally:
        db.close()

    return None


def create_client(client_name,
                  client_id,
                  client_secret,
                  redirect_uri,
                  client_type='confidential'):
    client = Client( client_name,
                     client_id,
                     client_secret,
                     redirect_uri,
                     client_type)
    try:
        db = DB(SERVER, PORT)
        db.dbroot[client_id] = client
        transaction.commit()
        
        return client
    except Exception, e:
        logging.error('create_client: %s' %(str(e)))
        transaction.abort()
    finally:
        db.close()
        
    return None




def client_exists(client_id):
    try:
        db = DB(SERVER, PORT)
        if client_id in db.dbroot:
            return True
    except Exception, e:
        logging.error('client_exists: %s' % (str(e)))
    finally:
        db.close()
        
    return False



def get_client(client_id):
    try:
        db = DB(SERVER, PORT)
        if client_id in db.dbroot:
            client = db.dbroot[client_id]
            
            return deepcopy(client)
    except Exception, e:
        logging.error('get_client' + str(e))
    finally:
        db.close()
    
    return None


    


def get_password(username):
    try:
        db = DB(SERVER, PORT)
        if username in db.dbroot:
            user = db.dbroot[username]
            return user.password
    except Exception, e:
        logging.error('get_password(): %s' % (str(e)))
    finally:
        db.close()

    return None


def get_user(uid=None):
    try:
        db = DB(SERVER, PORT)
        if uid is not None:
            user = db.dbroot[uid]

            return deepcopy(user)
        elif cherrypy.request.login in db.dbroot:
            user = db.dbroot[cherrypy.request.login]
    
            return deepcopy(user)
    except Exception, e:
        logging.error('get_user: %s' % (str(e)))
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
    except Exception, e:
        logging.error('create_auth_code %s' % (str(e)))
    finally:
        db.close()

    return None



def get_auth_code(client_id, client_secret, code):
    try:
        db = DB(SERVER, PORT)
        if code in db.dbroot:
            auth_code = deepcopy(db.dbroot[code])
                
            if auth_code.expire + auth_code.created > time() and \
                   auth_code.client.id == client_id and \
                   auth_code.client.secret == client_secret:
                return auth_code
    except Exception, e:
        logging.error('get_auth_code: %s' % (str(e)))
    finally:
        db.close()


    return False



def create_access_token_from_code(auth_code):
    try:
        db = DB(SERVER, PORT)
    
        client = db.dbroot[auth_code.client.id]
        user = db.dbroot[auth_code.user.id]
        token = AccessToken(client,
                            user,
                            scope=auth_code.scope)
        db.dbroot[token.code] = token
        transaction.commit()

        return token.code
    except Exception, e:
        logging.error('create_access_token_from_code: %s' % (str(e)))
    finally:
        db.close()
    
    return False


def create_implicit_grant_access_token(client_id, redirect_uri, scope=None):
    try:
        user = get_user()
        db = DB(SERVER, PORT)
        client = db.dbroot[client_id]
        
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
            logging.warn('%s uri of %s does not match %s' %
                         (client_id, client.redirect_uri, redirect_uri))
    except Exception, e:
        logging.error('%s' % (str(e)))
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
        #then I don't have to change anything below
        client_secret = password
    user = get_user(user_id)
    try:
        db = DB(SERVER, PORT)
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
        logging.error('create_access_token_from_user_pass: %s' %
                      (str(e)))
    finally:
        db.close()

    return False



def create_access_token_from_refresh_token(refresh_token):
    '''
    We assume that in the getting of the refresh_token,
    before calling this function, the authentication takes place there.
    '''
    try:
        #disconnect the data reference from the data stored in the DB
        refresh_token = deepcopy(refresh_token)

        #use the info stored in the refresh_token copy to create a
        #new AccessToken
        token = AccessToken(refresh_token.client,
                            refresh_token.user,
                            refresh_token.scope)
    
        #delete old access_token and create a new access_token
        #to replace the old one. refresh_token.access_token is
        #the string code not an AccessToken object
        delete_token(refresh_token.access_token)
        db = DB(SERVER, PORT)
        db.dbroot[token.code] = token
        refresh_token.access_token = token
        refresh_token._p_changed = True
        transaction.commit()

        #return access token string not AccessToken object
        return token.code
    except Exception, e:
        logging.error('create_access_token_from_refresh_token: %s' %
                      str(e))
        transaction.abort()
    finally:
        db.close()

    return False



def create_refresh_token_from_code(auth_code, access_token):
    try:
        db = DB(SERVER, PORT)
        auth_code = deepcopy(auth_code)
        token = RefreshToken(access_token,
                             auth_code.client,
                             auth_code.user,
                             scope=auth_code.scope)
        db.dbroot[token.code] = token
        transaction.commit()
        
        return token.code
    except Exception, e:
        logging.error('create_refresh_token_from_code %s' % (str(e)))
        transaction.abort()
    finally:
        db.close()

    return False


def create_refresh_token_from_user_pass(client_id,
                                        client_secret,
                                        user_id,
                                        password,
                                        scope,
                                        access_token):
    try:
        client = None
        if client_id != None:
            client = get_client(client_id)
        else:
            #not using client credentials do just create
            #a client object from user credentials
            client = Client(user_id, user_id, password, None)
            #make client_secret equal password
            client_secret = password
            
        user = get_user(user_id)
        if client != None and \
               user != None and \
               client.secret == client_secret and \
               user.password == password:
            try:
                db = DB(SERVER, PORT)
                token = RefreshToken(access_token,
                                     client,
                                     user,
                                     scope=scope)
                db.dbroot[token.code] = token
                transaction.commit()

                return token.code
            except Exception, e:
                logging.error('create_refresh_token_from_user_pass: %s' %
                              (str(e)))
                transaction.abort()
            finally:
                db.close()
    except Exception, e:
        logging.error('create_refresh_token_from_user_pass: %s' %
                      (str(e)))
    

    return False


def get_token(client_id, client_secret, code):
    '''
    This function should get any type of token
    since the code is unique and should only
    return the type of token that was created
    in create_[...]_token
    '''
    try:
        db = DB(SERVER, PORT)
        if code in db.dbroot:
            token = deepcopy(db.dbroot[code])
        
            if (not token.expire or token.expire + token.created > time()) and \
                   token.client.id == client_id and \
                   token.client.secret == client_secret:
            
                return token
            else:
                logging.warn('get_token: Did not authenticate')
        else:
            logging.warn('get_token: code %s is not in database' % (code))
    except Exception, e:
        logging.error('get_token(%s, %s %s): %s' %
                      (client_id, client_secret, code, str(e)))
    finally:
        db.close()

    return False



def get_access_token(token_str):
    try:
        db = DB(SERVER, PORT)
        if token_str in db.dbroot:
            token = deepcopy(db.dbroot[token_str])
            
            if isinstance(token, AccessToken) and \
                   not token.expire or \
                   token.expire + token.created > time():
                return token
            else:
                logging.warn('get_access_token: Token %s has expired for client %s and user %s' %
                             (token.code, token.client.id, token.user.id))
        else:
            logging.warn('get_access_token: token %s is not in database' % (token_str))
    except Exception, e:
        logging.error('get_access_token(%s): %s' %
                      (token_str, str(e)))
    finally:
        db.close()
            
    return False


def delete_token(token):
    try:
        db = DB(SERVER, PORT)
        if isinstance(token, AuthCode):
            del db.dbroot[token.code]
        else:
            del db.dbroot[token]
        transaction.commit()
    except Exception, e:
        logging.error('delete_token: %s' % (str(e)))
        transaction.abort()
    finally:
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

            
        def test_get_auth_code(self):
            client = Client(TestDBFunctions.client_name,
                            TestDBFunctions.client_id,
                            TestDBFunctions.client_secret,
                            TestDBFunctions.redirect_uri,
                            TestDBFunctions.client_type)
            cherrypy.request.login = TestDBFunctions.user_id
            
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            code = AuthCode(client, user)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            db.dbroot[TestDBFunctions.client_id] = client
            db.dbroot[code.code] = code
            transaction.commit()
            db.close()


            code2 = get_auth_code(TestDBFunctions.client_id,
                                  TestDBFunctions.client_secret,
                                  code.code)
            self.assertIsNotNone(code2)
            self.assertTrue(code2 != False)
            self.assertEqual(code2.code, code.code)
            self.assertEqual(code2.client.id, code.client.id)
            self.assertEqual(code2.user.id, code.user.id)



        def test_create_access_token_from_code(self):
            client = Client(TestDBFunctions.client_name,
                            TestDBFunctions.client_id,
                            TestDBFunctions.client_secret,
                            TestDBFunctions.redirect_uri,
                            TestDBFunctions.client_type)
            cherrypy.request.login = TestDBFunctions.user_id
            
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            code = AuthCode(client, user)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            db.dbroot[TestDBFunctions.client_id] = client
            db.dbroot[code.code] = code
            transaction.commit()
            db.close()

            token = create_access_token_from_code(code)
            
            self.assertIsNotNone(token)
            self.assertTrue(token != False)
            
            try:
                db = DB(SERVER, PORT)
                self.assertTrue(token in db.dbroot)
                self.assertEqual(db.dbroot[token].code, token)
            except Exception, e:
                self.fail(str(e))
            finally:
                db.close()
            

        def test_create_access_token_from_user_pass(self):
            client = Client(TestDBFunctions.client_name,
                            TestDBFunctions.client_id,
                            TestDBFunctions.client_secret,
                            TestDBFunctions.redirect_uri,
                            TestDBFunctions.client_type)
            cherrypy.request.login = TestDBFunctions.user_id
            
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            code = AuthCode(client, user)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            db.dbroot[TestDBFunctions.client_id] = client
            db.dbroot[code.code] = code
            transaction.commit()
            db.close()

            token = create_access_token_from_user_pass(
                TestDBFunctions.client_id,
                TestDBFunctions.client_secret,
                TestDBFunctions.user_id,
                TestDBFunctions.user_password,
                '')

            self.assertIsNotNone(token)
            self.assertTrue(token != False)
            
            try:
                db = DB(SERVER, PORT)
                self.assertTrue(token in db.dbroot)
                self.assertEqual(db.dbroot[token].code, token)
            except Exception, e:
                self.fail(str(e))
            finally:
                db.close()
                

        def test_create_access_token_from_refresh_token(self):
            client = Client(TestDBFunctions.client_name,
                            TestDBFunctions.client_id,
                            TestDBFunctions.client_secret,
                            TestDBFunctions.redirect_uri,
                            TestDBFunctions.client_type)
            cherrypy.request.login = TestDBFunctions.user_id
            
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            code = AccessToken(client, user)
            refresh = RefreshToken(code.code, client, user)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            db.dbroot[TestDBFunctions.client_id] = client
            db.dbroot[code.code] = code
            db.dbroot[refresh.code] = refresh
            transaction.commit()
            db.close()

            token = create_access_token_from_refresh_token(refresh)

            self.assertIsNotNone(token)
            self.assertTrue(token != False)
            
            try:
                db = DB(SERVER, PORT)
                self.assertTrue(token in db.dbroot)
                self.assertEqual(db.dbroot[token].code, token)
            except Exception, e:
                self.fail(str(e))
            finally:
                db.close()



        def test_create_refresh_token_from_code(self):
            client = Client(TestDBFunctions.client_name,
                            TestDBFunctions.client_id,
                            TestDBFunctions.client_secret,
                            TestDBFunctions.redirect_uri,
                            TestDBFunctions.client_type)
            cherrypy.request.login = TestDBFunctions.user_id
            
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            code = AuthCode(client, user)
            access = AccessToken(client, user)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            db.dbroot[TestDBFunctions.client_id] = client
            db.dbroot[code.code] = code
            db.dbroot[access.code] = access
            transaction.commit()
            db.close()

            token = create_refresh_token_from_code(code, access.code)

            self.assertIsNotNone(token)
            self.assertTrue(token != False)
            
            try:
                db = DB(SERVER, PORT)
                self.assertTrue(token in db.dbroot)
                self.assertEqual(db.dbroot[token].code, token)
            except Exception, e:
                self.fail(str(e))
            finally:
                db.close()



        def test_create_refresh_token_from_user_pass(self):
            client = Client(TestDBFunctions.client_name,
                            TestDBFunctions.client_id,
                            TestDBFunctions.client_secret,
                            TestDBFunctions.redirect_uri,
                            TestDBFunctions.client_type)
            cherrypy.request.login = TestDBFunctions.user_id
            
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            code = AuthCode(client, user)
            access = AccessToken(client, user)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            db.dbroot[TestDBFunctions.client_id] = client
            db.dbroot[code.code] = code
            db.dbroot[access.code] = access
            transaction.commit()
            db.close()

            token = create_refresh_token_from_user_pass(
                TestDBFunctions.client_id,
                TestDBFunctions.client_secret,
                TestDBFunctions.user_id,
                TestDBFunctions.user_password,
                '',
                access.code)

            self.assertIsNotNone(token)
            self.assertTrue(token != False)
            
            try:
                db = DB(SERVER, PORT)
                self.assertTrue(token in db.dbroot)
                self.assertEqual(db.dbroot[token].code, token)
            except Exception, e:
                self.fail(str(e))
            finally:
                db.close()


        def test_get_token(self):
            client = Client(TestDBFunctions.client_name,
                            TestDBFunctions.client_id,
                            TestDBFunctions.client_secret,
                            TestDBFunctions.redirect_uri,
                            TestDBFunctions.client_type)
            cherrypy.request.login = TestDBFunctions.user_id
            
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            code = AuthCode(client, user)
            access = AccessToken(client, user)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            db.dbroot[TestDBFunctions.client_id] = client
            db.dbroot[code.code] = code
            db.dbroot[access.code] = access
            transaction.commit()
            db.close()

            #we'll get the access token here
            token = get_token(TestDBFunctions.client_id,
                              TestDBFunctions.client_secret,
                              access.code)

            self.assertIsNotNone(token)
            self.assertTrue(token != False)
            
            try:
                db = DB(SERVER, PORT)
                self.assertTrue(token.code in db.dbroot)
                self.assertEqual(db.dbroot[token.code].code, token.code)
            except Exception, e:
                self.fail(str(e))
            finally:
                db.close()


        def test_delete_token_object(self):
            client = Client(TestDBFunctions.client_name,
                            TestDBFunctions.client_id,
                            TestDBFunctions.client_secret,
                            TestDBFunctions.redirect_uri,
                            TestDBFunctions.client_type)
            cherrypy.request.login = TestDBFunctions.user_id
            
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            code = AuthCode(client, user)
            access = AccessToken(client, user)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            db.dbroot[TestDBFunctions.client_id] = client
            db.dbroot[code.code] = code
            db.dbroot[access.code] = access
            transaction.commit()
            db.close()


            delete_token(code)

            try:
                db = DB(SERVER, PORT)
                self.assertFalse(code.code in db.dbroot)
            except Exception, e:
                self.fail(str(e))
            finally:
                db.close()


        def test_delete_token_code_str(self):
            client = Client(TestDBFunctions.client_name,
                            TestDBFunctions.client_id,
                            TestDBFunctions.client_secret,
                            TestDBFunctions.redirect_uri,
                            TestDBFunctions.client_type)
            cherrypy.request.login = TestDBFunctions.user_id
            
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            code = AuthCode(client, user)
            access = AccessToken(client, user)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            db.dbroot[TestDBFunctions.client_id] = client
            db.dbroot[code.code] = code
            db.dbroot[access.code] = access
            transaction.commit()
            db.close()


            delete_token(code.code)

            try:
                db = DB(SERVER, PORT)
                self.assertFalse(code.code in db.dbroot)
            except Exception, e:
                self.fail(str(e))
            finally:
                db.close()


        def test_get_access_token(self):
            client = Client(TestDBFunctions.client_name,
                            TestDBFunctions.client_id,
                            TestDBFunctions.client_secret,
                            TestDBFunctions.redirect_uri,
                            TestDBFunctions.client_type)
            cherrypy.request.login = TestDBFunctions.user_id
            
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            code = AuthCode(client, user)
            access = AccessToken(client, user)
            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            db.dbroot[TestDBFunctions.client_id] = client
            db.dbroot[code.code] = code
            db.dbroot[access.code] = access
            transaction.commit()
            db.close()


            token = get_access_token(access.code)
            
            self.assertFalse(isinstance(token, AuthCode))
            self.assertFalse(isinstance(token, RefreshToken))
            self.assertTrue(isinstance(token, AccessToken))
            
            
                
    main()
    
    
