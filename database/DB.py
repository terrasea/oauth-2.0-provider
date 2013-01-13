from models import RefreshToken

import logging as logmodule
import time


logging = logmodule.getLogger('oauth DB')


SERVER = 'localhost'
PORT = 6000

ZODB=0
MONGO=1
POSTGRE=2
MYSQL=3

DBTYPE=MONGO


class BaseDB(object):
    def __init__(self, collection=None, server=None, port=None):
        pass


    def get(self, key):
        pass


    def put(self, key, value):
        pass


    def update(self, key, value):
        pass


    def delete(self, key):
        pass


    def contains(self, key):
        pass


    def close(self):
        pass


def singletonconnection(cls):
    instances = dict()
    @classmethod
    def close(cls):
        return

    origclose = cls.close
    cls.close = close
    cls.origclose = origclose
    
    def getinstance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
            
        logging.warn('cls is ' + str(cls))

        return instances[cls]


    return getinstance



if MONGO == DBTYPE:
    from pymongo import Connection
    from pymongo.son_manipulator import SONManipulator
    import jsonpickle
    import json



    class Transform(SONManipulator):
        """
        Used to transparently transform class objects to dicts and back again.  This is done using jsonpickle and json modules. jsonpickle to create a json string of an object, json to turn this into a python dict or list and store in MongoDB.  On getting from DB, use json to turn dict/list to a string json value and use jsonpickle to turn this json string into the object it represents
        """
        def transform_incoming(self, son, collection):
            for (key, value) in son.items():
                if 'class' == key:
                    son[key] = json.loads(jsonpickle.encode(value))
                    logging.warn('in ' + str(son[key]))
                elif isinstance(value, dict):
                    son[key] = self.transform_incoming(value, collection)
            return son


        def transform_outgoing(self, son, collection):
            for (key, value) in son.items():
                if 'class' == key:
                    son[key] = jsonpickle.decode(json.dumps(value))
                    logging.warn('out ' + str(son[key]))
                elif isinstance(value, dict):
                    son[key] = self.transform_outgoing(value, collection)
            return son



    #connection pooling is already done on
    #MongoDB Connections behind the scenes
    class DB(BaseDB):
        def __init__(self, collection=None, server=None, port=None, connection=None):
            super(DB).__init__(collection, server, port)
            if connection is None:
                self.connection = Connection()
            else:
                self.connection = connection
            
            self.db = self.connection['oauth']
            #make sure the Tranform class which is a SONManipulator is used
            self.db.add_son_manipulator(Transform())
            
            if collection is not None:
                self.models = self.db.models.collection
            else:
                self.models = self.db.models
                


        def get(self, key):
            document = self.models.find_one({'key':key})
            
            return document['class']


        def put(self, key, data):
            #if we don't do this we end up with mutiple copies of the same data
            if not self.contains(key):
                document = {'key':key, 'class': data}
                self.models.insert(document)
            else:
                self.update(key, data)
                    

        def update(self, key, data):
            #import pdb; pdb.set_trace()
            #seems you can't use a SONManipulator on updates,
            #manipulate=True also adds a new _id which causes an
            #'OperationFailure: Modifiers and non-modifiers cannot be mixed'
            #Solution: do the transform directly and use the result to
            #update the entry with and don't set manipulate=True
            data = json.loads(jsonpickle.encode(data))
            self.models.update({'key':key}, {"$set": {'class':data}}, multi=False, safe=True)
            

        def delete(self, key):
            self.models.remove({'key':key})


        def contains(self, key):
            #self.models.find_one returns None
            #if no entry with that key filter exists
            #so wrapping it in bool will return False if None,
            #True on anything else
            return bool(self.models.find_one({'key':key}))


        def close(self):
            self.connection.close()



elif POSTGRE == DBTYPE:
    import psycopg2
    
    class DB(BaseDB):
        def __init__(self, collection=None, server=None, port=None):
            super(DB).__init__(collection, server, port)
            self.connection = psycopg2.connect("dbname='oauth' user='terrasea' host='localhost' password=''")
            self.cursor = connection.cursor()
            self.table = collection
            pass

        def get(self, key):
            pass


        def put(self, key, data):
            pass

        

        def update(self, key, data):
            pass


        def delete(self, key):
            pass

        def commit(self):
            pass


        def abort(self):
            pass


        def contains(self, key):
            pass


        def close(self):
            self.cursor.close()
            self.connection.close()
            
elif MYSQL == DBTYPE:
    pass
else:
    pass
