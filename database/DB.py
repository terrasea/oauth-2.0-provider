import cherrypy
import logging
import array
from models import Association, User, Client, \
     AuthCode, AccessToken, RefreshToken
from ZEO.ClientStorage import ClientStorage
from ZODB import DB as ZDB
import transaction
from time import time
from copy import deepcopy
from errors import *

#from client import get_client

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



    


def get_password(username):
    db = DB(SERVER, PORT)
    try:
        if username in db.dbroot:
            user = db.dbroot[username]
            return user.password
    except Exception, e:
        logging.error(''.join(['get_password(): ', str(e)]))
    finally:
        db.close()

    return None


def get_user(uid=None):
    db = DB(SERVER, PORT)
    try:
        if uid is not None:
            user = db.dbroot[uid]

            return deepcopy(user)
        elif cherrypy.request.login in db.dbroot:
            user = db.dbroot[cherrypy.request.login]
    
            return deepcopy(user)
    except Exception, e:
        logging.error(''.join(['get_user: ', str(e)]))
    finally:
        db.close()

    return None


def add_user(uid, password, firstname=None, lastname=None):
    user = User(uid, password, firstname, lastname)
    db = DB(SERVER, PORT)
    try:
        if uid not in db.dbroot:
            db.dbroot[uid] = user
            transaction.commit()
        else:
            logging.warn(''.join(['add_user: ', str(uid), ' already exists']))
            raise UserExistsWarning(''.join(['User ', str(uid), ' already exists']))
    except Exception, e:
        logging.error(''.join(['add_user: ', (str(e))]))
        transaction.abort()
        
        return None
    finally:
        db.close()

        
    return user



def delete_user(user):
    pass



def associate_client_with_user(user, client, refresh_token_str):
    """
    Adds client to list of authorised clients who can access the users resources on a long term basis
    """

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
        if key in db.dbroot:
            association = db.dbroot[key]
            if client.id not in association.clients:
                # get the refresh token which contains the client,
                # user and access token, as well as the
                # refresh_token code. This allows us to delete the
                # access token and the refresh_token stopping the
                # client from accessing the users resources.
                association.clients[client.id] = get_token(client.id,
                                                           client.secret,
                                                           refresh_token_str)
                association._p_changed = True
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
            db.dbroot[key] = association
            
        transaction.commit()
    except Exception, e:
        logging.error(''.join(['associate_client_with_user: ', str(e)]))
        raise e
        transaction.abort()
    finally:
        db.close()




def get_associations(user):
    db = DB(SERVER, PORT)
    try:
        key = 'client_association_' + str(user.id)
        if key in db.dbroot:
            return deepcopy(db.dbroot[key])
    except Exception, e:
        logging.error('get_associations: ' + str(e))
    finally:
        db.close()

    return False



def create_auth_code(client_id, scope=None):
    client = get_client(client_id)
    user = get_user()
    db = DB(SERVER, PORT)
    try:
        auth_code = AuthCode(client, user, scope=scope)
        db.dbroot[auth_code.code] = auth_code
        transaction.commit()
        code = deepcopy(auth_code.code)
        return code
    except Exception, e:
        logging.error(''.join(['create_auth_code: ', str(e)]))
        transaction.abort()
    finally:
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



def create_access_token_from_code(auth_code):
    db = DB(SERVER, PORT)
    try:
        client = db.dbroot[auth_code.client.id]
        user = db.dbroot[auth_code.user.id]
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


def create_implicit_grant_access_token(client_id, redirect_uri, scope=None):
    user = get_user()
    db = DB(SERVER, PORT)
    try:
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



def create_refresh_token_from_code(auth_code, access_token):
    db = DB(SERVER, PORT)
    
    try:
        auth_code = deepcopy(auth_code)
        token = RefreshToken(access_token,
                             auth_code.client,
                             auth_code.user,
                             scope=auth_code.scope)
        db.dbroot[token.code] = token
        transaction.commit()
        
        return token.code
    except Exception, e:
        logging.error(''.join(['create_refresh_token_from_code ', str(e)]))
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
            db = DB(SERVER, PORT)
            try:
                token = RefreshToken(access_token,
                                     client,
                                     user,
                                     scope=scope)
                db.dbroot[token.code] = token
                
                transaction.commit()

                return token.code
            except Exception, e:
                logging.error(''.join(['create_refresh_token_from_user_pass: ',
                                       str(e)]))
                transaction.abort()
            finally:
                db.close()
    except Exception, e:
        logging.error(''.join(['create_refresh_token_from_user_pass: ',
                               str(e)]))
    

    return False


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
        
            if (not token.expire or token.expire + token.created > time()) and \
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
        else:
            del db.dbroot[token]
        transaction.commit()
    except Exception, e:
        logging.error('delete_token: ' + str(e))
        transaction.abort()
    finally:
        db.close()
    


if __name__ == '__main__j':
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




        def test_add_user(self):
            add_user(TestDBFunctions.user_id,
                     TestDBFunctions.user_password,
                     firstname='Jim',
                     lastname='Hudson')

            db = DB(SERVER, PORT)

            try:
                user = db.dbroot[TestDBFunctions.user_id]
                self.assertEqual(TestDBFunctions.user_id, user.id)
                self.assertEqual(TestDBFunctions.user_password, user.password)
                self.assertEqual('Jim', user.firstname)
                self.assertEqual('Hudson', user.lastname)
            finally:
                db.close()






        def test_associate_client_with_user(self):
            user = User(TestDBFunctions.user_id,
                        TestDBFunctions.user_password)
            client = Client(TestDBFunctions.client_name,
                            TestDBFunctions.client_id,
                            TestDBFunctions.client_secret,
                            TestDBFunctions.redirect_uri,
                            TestDBFunctions.client_type)

            db = DB(SERVER, PORT)
            db.dbroot[TestDBFunctions.user_id] = user
            db.dbroot[TestDBFunctions.client_id] = client
            before_length = len(db.dbroot)
            transaction.commit()
            db.close()

            

            associate_client_with_user(user, client)
            key = ''.join(['client_association_', str(user.id)])
            db = DB(SERVER, PORT)
            
            try:
                after_length = len(db.dbroot)
                self.assertNotEqual(before_length, after_length)
                self.assertTrue(key in db.dbroot)
                assoc = db.dbroot[key]
                self.assertEqual(TestDBFunctions.user_id, assoc.user.id)
                
                self.assertTrue(TestDBFunctions.client_id in assoc.clients)
                client2 = assoc.clients[TestDBFunctions.client_id]
                self.assertEqual(TestDBFunctions.client_id, client2.id)
            finally:
                db.close()



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
    
    
