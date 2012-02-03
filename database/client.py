from DB import DB, SERVER, PORT
from models import Client
from errors import ClientExistsWarning
import transaction
import logging
from copy import deepcopy

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
    db = DB(SERVER, PORT)
    try:
        if client_id not in db.dbroot:
            db.dbroot[client_id] = client
            transaction.commit()
            
            return client
        else:
            raise ClientExistsWarning(''.join(['Client with id of ',str(client_id), ' already exists']))
        
        
    except Exception, e:
        logging.error(''.join(['create_client: ', str(e)]))
        transaction.abort()
    finally:
        db.close()
        
    return None




def client_exists(client_id):
    db = DB(SERVER, PORT)
    try:
        if client_id in db.dbroot:
            return True
    except Exception, e:
        logging.warn(''.join(['client_exists: ', str(e)]))
    finally:
        db.close()
        
    return False



def get_client(client_id):
    db = DB(SERVER, PORT)
    try:
        if client_id in db.dbroot:
            client = db.dbroot[client_id]
            
            return deepcopy(client)
    except Exception, e:
        logging.error(''.join(['get_client', str(e)]))
    finally:
        db.close()
    
    return None




def delete_client(client_id):
    db = DB(SERVER, PORT)
    try:
        if client_id in db.dbroot:
            del db.dbroot[client_id]
            transaction.commit()
            
            return True
        else:
            logging.info('remove_client: client of ' + \
                         str(client_id) + ' does not exist')
    except Exception, e:
        transaction.abort()
        logging.error('remove_client: ' + str(e))
    finally:
        db.close()

    return False


if __name__ == '__main__':
    client = create_client('bob',
                           'bobby',
                           'iamcool',
                           'http://whaever.com')
    print client.id
    print client_exists('bobby')
    print get_client('bobby')
    print delete_client('bobby')
