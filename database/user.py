from DB import DB, SERVER, PORT
from models import User

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


if __name__ == '__main__':
    pass
