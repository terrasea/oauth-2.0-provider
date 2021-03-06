"""
Carries out the responsiblity of authenticating
the client application/program and resource owner/user
"""

from cherrypy import expose, HTTPRedirect, config, tools, request
from Cheetah.Template import Template
from cStringIO import StringIO
from urllib import urlencode
import logging

import database.client
import database.user
import database.models
import database.scope
import database.authcode
import database.accesstoken
import database.refreshtoken
import database.tokens
import database.associations

from database.errors import *

from user_resource_grant import user_resource_grant


##Am not sure where to put the associate clients with users code calls.
##
##

class Provider(object):
    """
    Authorises clients to access user resources and provides authorisation codes as well as access and refresh tokens.
    """
    def __init__(self, scope=tuple()):
        self._available_scope = scope
    
    @expose
    def index(self, code=None, error=None):
        return "Hello World!"


    @expose
    def manage(self):
        pass


    
    @expose
    def auth(self,
             response_type=None,
             client_id=None,
             redirect_uri=None,
             scope = None,
             state = None):

        if response_type not in ('code','token'):
            
            #It can only be the value 'code'
            #redirect to redirect_uri
            #with error message as a parameter
            error_str = StringIO()
            error_str.write(redirect_uri)
            error_list = [('error', 'invalid_request',)]
            if state != None:
                error_list.append(('state', state,))
            error_str.write('?')
            error_str.write(urlencode(error_list))

            raise HTTPRedirect(error_str.getvalue())


        if not database.client.client_exists(client_id):
            
            #client is not found in db
            error_str = StringIO()
            error_str.write(redirect_uri)
            error_list = [('error', 'invalid_client')]
            if state != None:
                error_list.append(('state', state))
            error_str.write('?')
            error_str.write(urlencode(error_list))

            raise HTTPRedirect(error_str.getvalue())

    


        if scope != None:
            available = self.available_scope
            scope_list = scope.split()
            available_scope = [x for x in scope_list if x in available]
            if available_scope != scope_list:
                #all the values in the scope
                #must match one in the available list
                #since it doesn't return a invalid_scope error
                error_str = StringIO()
                error_str.write(redirect_uri)
                error_list = [('error', 'invalid_scope')]
                if state != None:
                    error_list.append(('state', state))
                error_str.write('?')
                error_str.write(urlencode(error_list))

                raise HTTPRedirect(error_str.getvalue())



        client = database.client.get_client(client_id)
        if client.redirect_uri != redirect_uri:
            #does not match one stored in DB for client
            error_str = StringIO()
            error_str.write(redirect_uri)
            error_list = [('error', 'redirect_uri_mismatch')]
            if state != None:
                error_list.append(('state', state))
            error_str.write('?')
            error_str.write(urlencode(error_list))
            raise HTTPRedirect(error_str.getvalue())

        uid = request.login
        user = database.user.get_user(uid)
        if user == None:
            #for some reason the user logged in is not in DB
            error_str = StringIO()
            error_str.write(redirect_uri)
            error_list = [('error', 'access_denied')]
            if state != None:
                error_list.append(('state', state))
            error_str.write('?')
            error_str.write(urlencode(error_list))
            raise HTTPRedirect(error_str.getvalue())

        

        #will have to redesign user_resource_grant template to
        #add the response type value so it knows how to format
        #the return URL
        grant = user_resource_grant()
        grant.client_id = client_id
        grant.user_id = user.id
        grant.redirect_uri = redirect_uri
        if scope:
            grant.scope = scope
            grant.message = "Allow %s to access to %s?" % (client.name, scope)
        else:
            grant.scope = None
            grant.message = "Allow %s to access all your resources?" % (client.name)
        
        grant.state = state
        


        grant.title = "Access grant"
        grant.action = "get_auth_code"


        if response_type == 'code':
            grant.token = None
            
            return str(grant)
        
        elif response_type == 'token':
            grant.token = True
            
            return str(grant)



    @expose
    def get_auth_code(self,
                  allow=None,
                  deny=None,
                  user_id=None,
                  client_id=None,
                  redirect_uri=None,
                  scope=None,
                  state=None,
                  token=None):
        if deny:
            error_str = StringIO()

            error_str.write(redirect_uri)

            error_list = [('error', 'access_denied')]

            if state != None:
                error_list.append(('state', state))

            if token:
                error_str.write('#')
            else:
                error_str.write('?')

            error_str.write(urlencode(error_list))

            raise HTTPRedirect(error_str.getvalue())
        elif allow:
            response_str = StringIO()

            response_str.write(redirect_uri)

            if token:
                response_str.write('#')
            else:
                response_str.write('?')

            response_list = list()
            if token:
                uid = request.login
                auth_token_str = \
                               database.accesstoken.create_implicit_grant_access_token(
                    uid,
                    client_id,
                    redirect_uri,
                    scope)

                if not auth_token_str:
                    logging.warn('token unauthorised: ' + str(auth_token_str));
                    ##Error not authorised
                    error_str = StringIO()

                    error_str.write(redirect_uri)

                    error_list = [('error', 'unauthorized_client')]

                    if state:
                        error_list.append(('state', state))

                    if token:
                        error_str.write('#')
                    else:
                        error_str.write('?')

                    error_str.write(urlencode(error_list))

                    raise HTTPRedirect(error_str.getvalue())


                ## the client is probably a javascript client which
                ## can't be trusted for more than one session. Thus
                ## the client does not get a refresh token in this flow
                auth_token = database.accesstoken.get_access_token(auth_token_str)
                response_list.append(('access_token', auth_token.code))
                response_list.append(('expires_in', auth_token.expire))
                response_list.append(('token_type', 'bearer'))
                if scope:
                    response_list.append(('scope', scope))

            else:
                ## This is the normal 2 headed snake authentication.
                ## The client is sent back an authorisation code,
                ## which it uses to gain an access token later.
                uid = request.login
                
                auth_code_str = database.authcode.create_auth_code(client_id, uid, scope)

                response_list.append(('code', auth_code_str))

            if state:
                ## State is optional, but if present must be returned
                ## back to the client.
                response_list.append(['state', state])



            response_str.write(urlencode(response_list))

            raise HTTPRedirect(response_str.getvalue())


        #if both allow and deny are
        #None or False then will fall through to here
        return "<html><head><title>A problem occured" + \
               "</title></head><body><div>A problem occured</div></body></html>"


    @expose
    @tools.json_out()
    def token(self,
              grant_type=None,
              client_id=None,
              client_secret=None,
              username=None,
              password=None,
              assertion_type=None,
              assertion=None,
              scope=None,
              code=None,
              refresh_token=None,
              redirect_uri=None,
              state=None):
        '''
        returns a json string containing the
        access token and/or refresh token.
        '''

        if 'authorization_code' == grant_type:
            return self.process_auth_code_grant(client_id,
                                                client_secret,
                                                scope,
                                                code,
                                                redirect_uri)
        elif 'password' == grant_type:
            return self.process_password_grant(client_id,
                                               client_secret,
                                               username,
                                               password,
                                               scope)
        elif 'client_credentials' == grant_type:
            return {'error' : 'invalid_grant' }
        elif 'assertion' == grant_type:
            return self.process_assertion_grant(client_id,
                                                client_secret,
                                                assertion_type,
                                                assertion,
                                                scope)
        elif 'refresh_token' == grant_type:
            return self.process_refresh_token_grant(client_id,
                                                    client_secret,
                                                    refresh_token)
        elif 'none' == grant_type:
            return {'error' : 'invalid_grant' }
        else:
            #the grant_type specified is not a valid one
            return {'error' : 'invalid_grant' }







    def process_auth_code_grant(self,
                                client_id,
                                client_secret,
                                scope,
                                code,
                                redirect_uri):

        client = database.client.get_client(client_id)

        auth_code = database.authcode.get_auth_code(client_id,
                                                    client_secret,
                                                    code)
        print client, auth_code, 
        if client:
            print redirect_uri, client.redirect_uri

        if auth_code and \
               client and \
               redirect_uri == client.redirect_uri:

            access_token_str = database.accesstoken.create_access_token_from_code(auth_code)

            refresh_token_str = database.refreshtoken.create_refresh_token_from_code(
                auth_code,
                access_token_str)
            
            if not access_token_str:
                return  { 'error' : 'access_denied' }


            tokens = {
                'access_token'  : access_token_str,
                'token_type'    : 'bearer',
                'expires_in'    : database.tokens.get_token(client_id,
                                                           client_secret,
                                                           access_token_str).expire,
                'refresh_token' : refresh_token_str,
                }

            if scope:
                tokens.update({'scope'         : scope})

            try:
                
                if not database.associations.isassociated(auth_code.user,
                                                          auth_code.client,
                                                          refresh_token_str):
                    
                    database.associations.associate_client_with_user(auth_code.user,
                                                                     auth_code.client,
                                                                     refresh_token_str)
                else:
                    #import pdb; pdb.set_trace()
                    database.associations.update_association(auth_code.user,
                                                             auth_code.client,
                                                             refresh_token_str)

            except AssociationExistsWarning, e:
                logging.warn('process_auth_code_grant: ' + str(e))
            finally:
                database.authcode.delete_auth_code(code)

            return tokens



        #something went wrong
        return {'error' : 'invalid_client' }


    def process_password_grant(self,
                               client_id,
                               client_secret,
                               username,
                               password,
                               scope):
        access_token = database.accesstoken.create_access_token_from_user_pass(
            client_id,
            client_secret,
            username,
            password,
            scope)
        refresh_token = database.refreshtoken.create_refresh_token_from_user_pass(
            client_id,
            client_secret,
            username,
            password,
            scope,
            access_token)
        if access_token is not None and \
               refresh_token is not None:
            #turn it into a AccessToken instance & RefreshToken instance
            if client_id != None:
                access_token = database.tokens.get_token(client_id,
                                                        client_secret,
                                                        access_token)
                refresh_token = database.tokens.get_token(client_id,
                                                         client_secret,
                                                         refresh_token)
            else:
                access_token = database.tokens.get_token(username,
                                                        password,
                                                        access_token)
                refresh_token = database.tokens.get_token(username,
                                                         password,
                                                         refresh_token)
            
            tokens = {
                'access_token'  : access_token.code,
                'token_type'    : 'bearer',
                'expires_in'    : access_token.expire,
                'refresh_token' : refresh_token.code,
                }
            if scope:
                tokens.update({'scope'         : scope})


            try:
                if not database.associations.isassociated(refresh_token.user,
                                                          refresh_token.client,
                                                          refresh_token):
                    database.associations.associate_client_with_user(refresh_token.user,
                                                                     refresh_token.client,
                                                                     refresh_token)
                else:
                    database.associations.update_association(refresh_token.user,
                                                             refresh_token.client,
                                                             refresh_token)

            except AssociationExistsWarning, e:
                logging.warn('process_auth_code_grant: ' + str(e))



            return tokens

        #something went wrong
        return {'error' : 'invalid_client' }




    def process_assertion_grant(self,
                                client_id,
                                client_secret,
                                assertion_type,
                                assertion,
                                scope):
        #I'm not going to support this yet
        return { 'error' : 'invalid_grant' }




    def process_refresh_token_grant(self,
                                    client_id,
                                    client_secret,
                                    refresh_token):


        token = database.tokens.get_token(client_id,
                                          client_secret,
                                          refresh_token)
        
        if not isinstance(token, database.models.RefreshToken):
            return { 'error' : 'invalid_grant' }

        access_token = token.access_token
        #database.tokens.delete_token(access_token)
        del access_token

        new_access_token = database.tokens.get_token(
            client_id,
            client_secret,
            database.accesstoken.create_access_token_from_refresh_token(token))

        tokens = {
            'access_token' : new_access_token.code,
            'token_type'   : 'bearer',
            'expires_in'   : new_access_token.expire,
            }

        if new_access_token.scope:
            tokens.update({'scope'        : new_access_token.scope})

        return tokens




    @property
    def available_scope(self):
        return self._available_scope


    @available_scope.setter
    def available_scope(self, scope):
        self._available_scope = scope




def access_resource_authorised(token_str):
    '''
    @attr token_str - the access token string representation
    
    @returns the AccessToken object for the token string on success or the error message in the form of a python dictionary
    '''
    token = database.accesstoken.get_access_token(token_str)
    
    expired = available_scope = scope_list = True

    #if token is not false or none checks to see if it is a AccessToken or not
    if token and isinstance(token, database.models.AccessToken):
        if token.scope == None or \
               token.scope != None and token.scope.lower() == 'all':
            return token
        elif token.scope != None and request.path_info in token.scope:
            return token
        else:
            return {'error':'insufficient_scope'}
    
    #assume to be a invalid token if it got this far
    return {'error':'invalid_token'}






def check(username, password):
    if database.user.get_password(username) != password:
        return u'Authentication failed'
    

def anonymous():
    urls = database.scope.get_anonymous_urls()

    if urls:
        urls.add('/oauth/token')
        if request.path_info in urls:
            return 'anonymous'
        
    



config.update({
    'tools.sessions.on': True,
    'tools.session_auth.on': True,
    'tools.session_auth.check_username_and_password':check,
    'tools.session_auth.anonymous':anonymous,
    })              











@expose
@tools.response_headers(headers = [('Content-Type', 'image/svg')])
def avatar(access_token=None):
    token = access_resource_authorised(access_token)
    if isinstance(token, database.models.AccessToken):
        user = token.user
        
        try:
            with open('users/%s/avatar.svg' % (user.id)) as avatar:
                return avatar.read()
        except IOError, io:
            logging.error(str(io))
            return None
            

    return str(token)

@expose
@tools.json_out()
def who_am_i(access_token=None):
    token = access_resource_authorised(access_token)
    if isinstance(token, database.models.AccessToken):
        user = database.user.get_user(token.user)
        logging.error(str(user))
        return {'id'        : user.id,
                'firstname' : user.firstname,
                'lastname'  : user.lastname,
                }

    #if it got this far then
    #something went wrong and
    #the token should be a
    #dict which represents the error
    return token
    


if __name__ == '__main__':
    from cherrypy import quickstart
    from urllib2 import urlopen, Request

    class Root(object):
        @expose
        def index(self, error=None, code=None, state=None):
            if error != None:
                return "<html><head><title>Index</title></head><body><div>This is the index where a error %s occured</div></body></html>" % (error)
            elif code != None:
                data = {'grant_type': 'authorization_code',
                        'client_id': 'o9999o',
                        'client_secret': 'secret',
                        'code': code,
                        'redirect_uri': 'http://127.0.0.1:8080',}
                request = Request('http://localhost:8080/oauth/token',
                                  urlencode(data))
                logging.info(str(request))
                response = urlopen(request)
                message = response.read()
                return "<html><head><title>Index</title></head><body><div>This is the index where the code is %s</div><div>%s</div><with a returned state of %s</div></body></html>" % (code, message, state)
            return "<html><head><title>Index</title></head><body><div>This is the index</div></body></html>"

    index = Root()

    index.oauth = Provider()

    index.who_am_i = who_am_i
    index.avatar = avatar

    database.scope.add_anonymous_url('/who_am_i')
    database.scope.add_anonymous_url('/avatar')

    quickstart(index)
