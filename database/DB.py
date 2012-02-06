from ZEO.ClientStorage import ClientStorage
from ZODB import DB as ZDB
import transaction
from persistent import Persistent

from models import RefreshToken

import logging

SERVER = 'localhost'
PORT = 6000
 
db = None
storage = None
connection = None
dbroot = None

class ZODB(object):
    def __init__(self, server=SERVER, port=PORT):
        global storage, db, connection, dbroot
        if not db:
            logging.warn('db is not set')
            self.storage = storage = ClientStorage((server, port,))
            self.db = db = ZDB(self.storage)
            self.connection = connection = self.db.open()
            self.dbroot = dbroot = self.connection.root()
        else:
            logging.warn('db is already set')
            self.storage = storage
            self.db = db
            self.connection = connection
            self.dbroot = dbroot


    # KISS policy
    # let the lookup raise its own exception on a key lookup problem, etc
    def get(self, key):
        return self.dbroot[key]


    def put(self, key, data):
        self.dbroot[key] = data

    def update(self, key, data, attribute=None, value=None):
        if isinstance(data, Persistent):
            data._p_changed = True
            #self.commit()
        else:
            self.dbroot[key] = data
            logging.warn('Not Persistent')

    def delete(self, key):
        if key in self.dbroot:
            del self.dbroot[key]
        else:
            logging.warn('key does not exist ' + key)

    def commit(self):
        transaction.commit()


    def abort(self):
        transaction.abort()
        
    def contains(self, key):
        return key in self.dbroot



    def close(self):
        pass


    def finish(self):
        self.connection.close()
        self.db.close()
        self.storage.close()













    


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
    
    
