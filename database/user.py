from DB import ZODB as DB, SERVER, PORT
from models import User
import transaction
import logging
from errors import *

from copy import deepcopy

def get_password(uid):
    db = DB(SERVER, PORT)
    try:
        if db.contains(uid):
            user = db.get(uid)
            return user.password
        else:
            logging.warn('get_password: user of uid ' + str(uid) + \
                         ' does not exist')
    except Exception, e:
        logging.error('get_password(): ' + str(e))
    finally:
        db.close()

    return None


def get_user(uid):
    db = DB(SERVER, PORT)
    try:
        if db.contains(uid):
            user = db.dbroot[uid]

            return deepcopy(user)
        else:
            logging.warn('get_user: user of uid ' + str(uid) + \
                         ' does not exist')
    except Exception, e:
        logging.error('get_user: ' + str(e))
    finally:
        db.close()

    return None


def add_user(uid, password, firstname=None, lastname=None):
    if not uid or not password:
        logging.error("add_user: can't add a user of uid " + str(uid) + \
                      " and password of " + str(password))
        return None
    user = User(uid, password, firstname, lastname)
    db = DB(SERVER, PORT)
    try:
        #if it doesn't exist add it else report it does
        if not db.contains(uid):
            db.put(uid, user)
            db.commit()
        else:
            logging.warn(''.join(['add_user: ', str(uid), ' already exists']))
            raise UserExistsWarning(''.join(['User ', str(uid), ' already exists']))
    except Exception, e:
        logging.error(''.join(['add_user: ', (str(e))]))
        db.abort()
        
        return None
    finally:
        db.close()

        
    return user



def delete_user(uid):
    db = DB(SERVER, PORT)
    try:
        if db.contains(uid):
            db.delete(uid)
            db.commit()
            return True
        else:
            logging.warn('delete_user: user of uid ' + str(uid) + \
                         ' does not exist')
    except Exception, e:
        logging.error('Error deleting user with uid ' + str(uid) + \
                      ': ' + str(e))
        db.abort()
    finally:
        db.close()

    return False

if __name__ == '__main__':
    #delete_user('jim')
    add_user('jim', 'password')
    add_user(None, None)
    user = get_user(None)
    user = get_user('jimbo')
    if user == None:
        user = get_user('jim')
    password = get_password('jimbo')
    if password == None:
        password = get_password(u'jim')
    if user and password:
        print user.id, user.password, password
    delete_user('jimbo')
    delete_user('jim')
    delete_user(None)
