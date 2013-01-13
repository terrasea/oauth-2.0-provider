import cherrypy
import logging

from cherrypy import tools


class RestfulClient(object):
    def __init__(self, client_api):
        self._api = client_api


    exposed = True
        
    
    
    def HEAD(self):
        """
        Needs to be defined here if you want head calls to be handle other than
        with 404.  Returns no content.
        """
        return
    
    @tools.json_out()
    def GET(self, client_id=None):
        """
        This method should not change the state of anything
        """
        cherrypy.response.headers["Content-Type"] = "application/json"
        try:
            if self._api.contains(client_id):
                client = self._api.get(client_id[1:])
                
                data = {'name': client.name, 'id': client.id, 'secret': client.secret, 'redirect_uri': client.redirect_uri, 'type': client.type}
                
                return data
                
            else:
                raise cherrypy.NotFound()
        except Exception, e:
            raise cherrypy.HTTPError(message=str(e))
    
    @tools.json_out()
    def PUT(self):
        data = cherrypy.request.body.read()
                
        return data
        
    @tools.json_out()
    def POST(self):
        data = cherrypy.request.body.read()
        
        return data

class API(object):
    def contains(self, client_id):
        if client_id == '90':
            return True
            
        return False
        
    def get(self, client_id):
        return {'id': 90, 'name': 'Joe 90', 'secret': 'password', 'redirect_uri': 'http://localhost', 'type': 'public'}
    
    
root = RestfulClient(API())
        
        
conf = {
    'global': {
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 8000,
    },
    '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
    }
}

cherrypy.quickstart(root, '/', conf)
