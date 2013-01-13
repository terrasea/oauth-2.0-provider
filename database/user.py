from DB import DB
from models import User
import transaction
import logging as logmodule
from errors import *

logging = logmodule.getLogger('oauth user')

from copy import deepcopy



class UserDB(DB):
    def __init__(self, server=None, port=None, connection=None):
        super(UserDB, self).__init__('User', server, port, connection)

    def add(self,
            uid,
            password,
            firstname=None,
            lastname=None):
        if not uid or not password:
            logging.error("add_user: can't add a user of uid " + str(uid) + \
                          " and password of " + str(password))
            return None
        user = User(uid, password, firstname, lastname)
        try:
            #if it doesn't exist add it else report it does
            if not self.contains(uid):
                self.put(uid, user)
            else:
                logging.warn(''.join(['add_user: ', str(uid), ' already exists']))
                raise UserExistsWarning(''.join(['User ', str(uid), ' already exists']))
        except Exception, e:
            logging.error(''.join(['add_user: ', (str(e))]))
            
            raise e
            
        return user




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
