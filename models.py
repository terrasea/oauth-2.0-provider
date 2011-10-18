"""
Contains all the DB models needed to store information
for the OAuth 2.0 provider
"""

from persistent import Persistent
from time import time
from uuid import uuid4

    

class Client(Persistent):
    """
    Represents a authorised client (program/application)
    storing the name of the client, and the client_id and client_secret as
    specified in OAuth 2.0 draft (draft-ietf-oauth-v2-22)
    """
    def __init__(self,
                 client_name,
                 client_id,
                 client_secret,
                 redirect_uri,
                 client_type='confidential'):
        self._client_name = client_name
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._client_type = client_type


    @property
    def name(self):
        return self._client_name


    @name.setter
    def name(self, client_name):
        self._client_name = client_name


    @property
    def id(self):
        return self._client_id


    @id.setter
    def id(self, client_id):
        self._client_id = client_id


    @property
    def secret(self):
        return self._client_secret


    @secret.setter
    def secret(self, client_secret):
        self._client_secret = client_secret


    @property
    def redirect_uri(self):
        return self._redirect_uri



    @redirect_uri.setter
    def redirect_uri(self, redirect_uri):
        self._redirect_uri = redirect_uri


    @property
    def type(self):
        return self._client_type


    @type.setter
    def type(self, client_type):
        self._client_type = client_type
        


class AuthCode(Persistent):
    """
    Represents the auth code created when a resource
    owner and client authenticates.

    Should be deleted after first use or after it expires.
    """
    def __init__(self, client, user, expire = 600):
        self._client = client
        self._user = user
        self._code = str(uuid4())
        self._expire = time() + expire

    @property
    def client(self):
        """
        Identifies the client application
        """
        return self._client


    @property
    def user(self):
        """
        identifies the resource owner
        """
        return self._user


    @property
    def code(self):
        """
        represents the authourisation
        code for the client to use to
        gain access to tokens used to
        gather the resource owners
        resources
        """
        return self._code


    @property
    def expire(self):
        """
        represents the time in seconds,
        since the Epoch, that the auth
        code should expire.  Max of ten
        minutes.
        """
        return self._expire



class User(Persistent):
    def __init__(self, user_id):
        self._id = user_id
        self._firstname = None
        self._lastname = None

    @property
    def id(self):
        return self._id


    @id.setter
    def id(self, user_id):
        self._id = user_id


    @property
    def firstname(self):
        return self._firstname


    @firstname.setter
    def firstname(self, name):
        self._firstname = name


    @property
    def lastname(self):
        return self._lastname


    @lastname.setter
    def lastname(self, name):
        self._lastname = name




class AccessToken(AuthCode):
    def __init__(self, client, user, expire = 3600):
        super(AccessToken, self).__init__(client, user, expire)
        


class RefreshToken(AuthCode):
    def __init__(self, client, user, expire = 0):
        super(AccessToken, self).__init__(client, user, expire)
        if expire == 0:
            self._expire = None


if __name__ == '__main__':
    from unittest import TestCase, main

    class TestClient(TestCase):
        def test_create_client(self):
            try:
                client = Client('test', '0909', '9089', 'https://localhost')
            except Exception, e:
                self.fail(str(e))


        def test_get_name(self):
            client = Client('test', '0909', '9089', 'https://localhost')
            self.assertEqual(client.name, 'test')


        def test_set_name(self):
            client = Client('test', '0909', '9089', 'https://localhost')
            client.name = 'test2'
            self.assertEqual(client.name, 'test2')


        def test_get_id(self):
            client = Client('test', '0909', '9089', 'https://localhost')
            self.assertEqual(client.id, '0909')


        def test_set_id(self):
            client = Client('test', '0909', '9089', 'https://localhost')
            client.id = '9999'
            self.assertEqual(client.id, '9999')


        def test_get_secret(self):
            client = Client('test', '0909', '9089', 'https://localhost')
            self.assertEqual(client.secret, '9089')


        def test_set_secret(self):
            client = Client('test', '0909', '9089', 'https://localhost')
            client.secret = '8888'
            self.assertEqual(client.secret, '8888')


        def test_get_redirect_uri(self):
            client = Client('test', '0909', '9089', 'https://localhost')
            self.assertEqual(client.redirect_uri, 'https://localhost')


        def test_set_redirect_uri(self):
            client = Client('test', '0909', '9089', 'https://localhost')
            client.redirect_uri = 'bhttps://localhost/target'
            self.assertEqual(client.redirect_uri, 'https://localhost/target')
        

        def test_get_type(self):
            client = Client('test', '0909', '9089', 'https://localhost')
            self.assertEqual(client.type, 'confidential')



        def test_set_type(self):
            client = Client('test', '0909', '9089', 'https://localhost')
            client.type = 'public'
            self.assertEqual(client.type, 'public')
            

    class TestAuthCode(TestCase):
        def test_create_authcode(self):
            try:
                AuthCode('client', 'user')
            except Exception, e:
                self.fail(str(e))


        def test_get_client(self):
            authcode = AuthCode('client', 'user')
            self.assertEqual(authcode.client, 'client')


        def test_get_user(self):
            authcode = AuthCode('client', 'user')
            self.assertEqual(authcode.user, 'user')


        def test_get_code(self):
            authcode = AuthCode('client', 'user')
            self.assertIsNotNone(authcode.code)


        def test_code_unique(self):
            #just create two instances and compare their codes
            authcode1 = AuthCode('client1', 'user')
            authcode2 = AuthCode('client2', 'user')
            self.assertNotEqual(authcode1.code, authcode2.code)


        def test_get_expire(self):
            authcode = AuthCode('client', 'user')
            self.assertGreaterEqual(authcode.expire, time())
            self.assertLessEqual(authcode.expire, time() + 600)
            

    class TestUser(TestCase):
        def test_create_user(self):
            try:
                User('test')
            except Exception, e:
                self.fail(str(e))


        def test_get_id(self):
            user = User('test')
            self.assertEqual(user.id, 'test')


        def test_set_id(self):
            user = User('test')
            user.id = 'test2'
            self.assertEqual(user.id, 'test2')


        def test_get_firstname(self):
            user = User('test')
            self.assertEqual(user.firstname, None)


        def test_set_firstname(self):
            user = User('test')
            user.firstname = 'firstname'
            self.assertEqual(user.firstname, 'firstname')


        def test_get_lastname(self):
            user = User('test')
            self.assertEqual(user.lastname, None)



        def test_set_lastname(self):
            user = User('test')
            user.lastname = 'lastname'
            self.assertEqual(user.lastname, 'lastname')

            
                          

    main()
    
