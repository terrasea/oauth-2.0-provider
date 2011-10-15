"""
Contains all the DB models needed to store information
for the OAuth 2.0 provider
"""

from persistent import Persistent
from datetime import datetime
from time import time
from uuid import uuid4

class Client(Persistent):
    """
    Represents a authorised client (program/application)
    storing the name of the client, and the client_id and client_secret as
    specified in OAuth 2.0 draft (draft-ietf-oauth-v2-22)
    """
    def __init__(self, client_name, client_id, client_secret):
        self._client_name = client_name
        self._client_id = client_id
        self._client_secret = client_secret


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



class AuthCode(Persistent):
    """
    Represents the auth code created when a resource owner and client authenticates 
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

        

if __name__ == '__main__':
    from unittest import TestCase, main

    class TestClient(TestCase):
        def test_create_client(self):
            try:
                client = Client('test', '0909', '9089')
            except Exception, e:
                self.fail(str(e))


        def test_get_name(self):
            client = Client('test', '0909', '9089')
            self.assertEqual(client.name, 'test')


        def test_set_name(self):
            client = Client('test', '0909', '9089')
            client.name = 'test2'
            self.assertEqual(client.name, 'test2')


        def test_get_id(self):
            client = Client('test', '0909', '9089')
            self.assertEqual(client.id, '0909')


        def test_set_id(self):
            client = Client('test', '0909', '9089')
            client.id = '9999'
            self.assertEqual(client.id, '9999')


        def test_get_secret(self):
            client = Client('test', '0909', '9089')
            self.assertEqual(client.secret, '9089')


        def test_set_secret(self):
            client = Client('test', '0909', '9089')
            client.secret = '8888'
            self.assertEqual(client.secret, '8888')
        


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
    
