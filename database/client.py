from DB import DB
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
    db = DB()
    try:
        if not db.contains(client_id):
            db.put(client_id, client)
            db.commit()
            
            return deepcopy(client)
        else:
            raise ClientExistsWarning(''.join(['Client with id of ',str(client_id), ' already exists']))
        
        
    except Exception, e:
        logging.error(''.join(['create_client: ', str(e)]))
        db.abort()
    finally:
        db.close()
        
    return None




def client_exists(client_id):
    db = DB()
    try:
        return db.contains(client_id)
    except Exception, e:
        logging.error(''.join(['client_exists: ', str(e)]))
    finally:
        db.close()
        
    return False



def get_client(client_id):
    db = DB()
    try:
        if db.contains(client_id):
            client = db.get(client_id)
            
            return deepcopy(client)
    except Exception, e:
        logging.error(''.join(['get_client', str(e)]))
    finally:
        db.close()
    
    return None




def delete_client(client_id):
    db = DB()
    try:
        if db.contains(client_id):
            db.delete(client_id)
            db.commit()
            
            return True
        else:
            logging.info('remove_client: client of ' + \
                         str(client_id) + ' does not exist')
    except Exception, e:
        logging.error('remove_client: ' + str(e))
        db.abort()
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
