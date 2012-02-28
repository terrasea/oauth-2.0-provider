from models import RefreshToken

import logging
import time

SERVER = 'localhost'
PORT = 6000

ZODB=0
MONGO=1
POSTGRE=2
MYSQL=3

DBTYPE=MONGO


class BaseDB(object):
    def __init__(self):
        raise NotImplemented()

    def get(self, key):
        pass

    def put(self, key, value):
        pass


    def update(self, key, value):
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


STALE_DURATION=60.0*3

def connection_pool(cls):
    used_pool = list()
    available_pool = list()
    
    def stale(entry):
        (conn, created) = entry
        now = time.time()
        return created + STALE_DURATION < now
    
    def clean():
        """
        removes all stale (old) connections from the pool
        """
        for x in available_pool:
            if stale(x):
                x[0].realclose()
                
        pool = [x for x in available_pool if stale(x)]
        for x in pool:
            available_pool.remove(x)
            
        

    def put_available(conn, created=time.time()):
        available_pool.append((conn, created))

    def put_used(conn, created=time.time()):
        used_pool.append((conn, created))

    def is_connection(conn, entry):
        return conn == entry[0]

    def used_to_available(conn):
        for entry in used_pool:
            if is_connection(conn, entry):
                used_pool.remove(entry)
                available_pool.append(entry)
                logging.warn('used_to_available found and swapped conn in lists')
                return
        logging.warn('used_to_available not found and swapped conn in lists')
        

    def close(cls):
        logging.warn('used to available ' + str(len(available_pool)) + ' ' + str(len(used_pool)))
        used_to_available(cls)
        logging.warn('used to available ' + str(len(available_pool)) + ' ' + str(len(used_pool)))

    def getconnection(*args, **kwargs):
        """
        returns the next available connection in the pool.  Creates a new one, adds it to the poll and returns that one, if no available connections exist.
        """
        clean()
        logging.warn('used & available ' + str(len(available_pool)) + ' ' + str(len(used_pool)))
        try:
            (conn, created) = available_pool.pop()
            put_used(conn, created)
            logging.warn('conn got from already available')
            logging.warn('used & available ' + str(len(available_pool)) + ' ' + str(len(used_pool)))
            return conn
        except Exception, e:
            logging.error(str(e))
            realclose = cls.close
            cls.close = close
            cls.realclose = realclose
            conn = cls(*args, **kwargs)
            logging.warn('new conn created')
            put_used(conn)
            logging.warn('used & available ' + str(len(available_pool)) + ' ' + str(len(used_pool)))
            return conn
    

    return getconnection


if ZODB == DBTYPE:
    from ZEO.ClientStorage import ClientStorage
    from ZODB import DB as ZDB
    import transaction
    from persistent import Persistent


    @singletonconnection
    class DB(BaseDB):
        def __init__(self, server=SERVER, port=PORT):
            self.storage = ClientStorage((server, port,))
            self.db = ZDB(self.storage)
            self.connection = self.db.open()
            self.dbroot = self.connection.root()


        # KISS policy
        # let the lookup raise its own exception on a key lookup problem, etc
        def get(self, key):
            return self.dbroot[key]


        def put(self, key, data):
            self.dbroot[key] = data

        def update(self, key, data):
            if isinstance(data, Persistent):
                data._p_changed = True
            else:
                self.dbroot[key] = data

        def delete(self, key):
            if key in self.dbroot:
                del self.dbroot[key]
            

        def commit(self):
            transaction.commit()


        def abort(self):
            transaction.abort()

        def contains(self, key):
            return key in self.dbroot



        def close(self):
            self.connection.close()
            self.db.close()
            self.storage.close()

elif MONGO == DBTYPE:
    from pymongo import Connection
    from pymongo.son_manipulator import SONManipulator
    import jsonpickle
    import json
    import inspect

    
    class Transform(SONManipulator):
        """
        Used to transparently transform class objects to dicts and back again.  This is done using jsonpickle and json modules. jsonpickle to create a json string of an object, json to turn this into a python dict or list and store in MongoDB.  On getting from DB, use json to turn dict/list to a string json value and use jsonpickle to turn this json string into the object it represents
        """
        def transform_incoming(self, son, collection):
            for (key, value) in son.items():
                if 'class' == key:
                    son[key] = json.loads(jsonpickle.encode(value))
                elif isinstance(value, dict):
                    son[key] = self.transform_incoming(value, collection)
            return son

        def transform_outgoing(self, son, collection):
            for (key, value) in son.items():
                if 'class' == key:
                    son[key] = jsonpickle.decode(json.dumps(value))
                elif isinstance(value, dict):
                    son[key] = self.transform_outgoing(value, collection)
            return son

    #connection pooling is already done on
    #MongoDB Connections behind the scenes
    class DB(BaseDB):
        def __init__(self):
            self.connection = Connection()
            self.db = self.connection['oauth']
            #make sure the Tranform class which is a SONManipulator is used
            self.db.add_son_manipulator(Transform())
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

        def commit(self):
            #we don't need this for MongoDB
            pass


        def abort(self):
            #we could do this I think,
            #but am currently debating whether to use it or not
            pass

        def contains(self, key):
            #returns None if no entry with that key filter exists
            #so wrapping it in bool will return False if None,
            #True on anything else
            return bool(self.models.find_one({'key':key}))


        def close(self):
            self.connection.close()
        
elif POSTGRE == DBTYPE:
    import psycopg2
    
    class DB(BaseDB):
        def __init__(self):
            self.connection = psycopg2.connect("dbname='oauth' user='terrasea' host='localhost' password=''")
            self.cursor = connection.cursor()
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
