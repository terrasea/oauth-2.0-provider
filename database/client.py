from DB import DB
from models import Client
from errors import ClientExistsWarning
import transaction
import logging
from copy import deepcopy


class ClientDB(DB):
    def __init__(self, server=None, port=None, connection=None):
        super(ClientAPI, self).__init__('Client', server, port, connection)


    def create(self,
               client_name,
               client_id,
               client_secret,
               redirect_uri,
               client_type='confidential'):
    
        client = Client( client_name,
                         client_id,
                         client_secret,
                         redirect_uri,
                         client_type)
        try:
            if not self.contains(client_id):
                self.put(client_id, client)
                self.commit()
                
                return client
            else:
                raise ClientExistsWarning(''.join(['Client with id of ',str(client_id), ' already exists']))
            
            
        except Exception, e:
            logging.error(''.join(['create_client: ', str(e)]))
            db.abort()
        finally:
            db.close()
            
        return None











if __name__ == '__main__':
    client = create_client('bob',
                           'bobby',
                           'iamcool',
                           'http://whaever.com')
    print client.id
    print client_exists('bobby')
    print get_client('bobby')
    print delete_client('bobby')
