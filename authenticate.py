"""
Carries out the responsiblity of authenticating
the client application/program and resource owner/user
"""

from cherrypy import expose, HTTPRedirect, config, tools, request
from Cheetah.Template import Template
from cStringIO import StringIO
from urllib import urlencode
import logging

from database import client_exists, get_client, \
     available_scope, get_password, get_user, \
     create_auth_code, get_auth_code as db_get_auth_code, \
     create_access_token_from_code, create_refresh_token_from_code, \
     get_token, create_access_token_from_user_pass, \
     create_refresh_token_from_user_pass, RefreshToken, \
     delete_token, create_access_token_from_refresh_token, AccessToken, \
     get_access_token as db_get_access_token, \
     create_implicit_grant_access_token
from user_resource_grant import user_resource_grant


def check(username, password):
    if get_password(username) != password:
        return u'Authentication failed'
    

def anonymous():
    if request.path_info in ('/token', '/who_am_i', '/avatar'):
        return 'anonymous'
    

def login_required(func):
    def wrap(*args, **kwargs):
        return func(args, kwargs)

    return wrap

def login_not_required(func):
    import cherrypy
    def wrap(*args, **kwargs):
        cherrypy.request.login = 'anonymous'
        return func(*args, **kwargs)

    return wrap


config.update({
    'tools.sessions.on': True,
    'tools.session_auth.on': True,
    'tools.session_auth.check_username_and_password':check,
    'tools.session_auth.anonymous':anonymous,
    })              



@expose
def authorise_client(response_type,
                     client_id,
                     redirect_uri,
                     scope = None,
                     state = None):
    print 'authorise'
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

    print 'client exista'
    if not client_exists(client_id):
        #client is not found in db
        error_str = StringIO()
        error_str.write(redirect_uri)
        error_list = [('error', 'invalid_client')]
        if state != None:
            error_list.append(('state', state))
        error_str.write('?')
        error_str.write(urlencode(error_list))
        raise HTTPRedirect(error_str.getvalue())

    

    print 'scope'
    if scope != None:
        available = available_scope()
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


    print 'get client'
    client = get_client(client_id)
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

    print 'get user'
    user = get_user()
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


    print 'set up template'
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
        
    if state:
        grant.state = state
    else:
        grant.state = None


    grant.title = "Access grant"
    grant.action = "get_auth_code"


    if response_type == 'code':
        grant.token = None
        return str(grant)
    elif response_type == 'token':
        grant.token = True
        return str(grant)



@expose
def get_auth_code(allow=None,
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
            auth_token_str = create_implicit_grant_access_token(client_id,
                                                                redirect_uri,
                                                                scope)
            if not auth_token_str:
                error_str = StringIO()
        
                error_str.write(redirect_uri)
                
                error_list = [('error', 'unauthorized_client')]
        
                if state != None:
                    error_list.append(('state', state))
            
                if token:
                    error_str.write('#')
                else:
                    error_str.write('?')
            
                error_str.write(urlencode(error_list))
        
                raise HTTPRedirect(error_str.getvalue())
                
            auth_token = db_get_access_token(auth_token_str)
            response_list.append(('access_token', auth_token.code))
            response_list.append(('expires_in', auth_token.expire))
            if scope:
                response_list.append(('scope', scope))
            
        else:
            auth_code_str = create_auth_code(client_id, scope)
            
            response_list.append(('code', auth_code_str))
        
        if state:
            response_list.append(['state', state])
            

            
        response_str.write(urlencode(response_list))
        
        raise HTTPRedirect(response_str.getvalue())


@expose
@tools.json_out()
def get_access_token(grant_type=None,
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
        return process_auth_code_grant(client_id,
                                       client_secret,
                                       scope,
                                       code,
                                       redirect_uri)
    elif 'password' == grant_type:
        return process_password_grant(client_id,
                                      client_secret,
                                      username,
                                      password,
                                      scope)
    elif 'client_credentials' == grant_type:
        pass
    elif 'assertion' == grant_type:
        return process_assertion_grant(client_id,
                                       client_secret,
                                       assertion_type,
                                       assertion,
                                       scope)
    elif 'refresh_token' == grant_type:
        return process_refresh_token_grant(client_id,
                                           client_secret,
                                           refresh_token)
    elif 'none' == grant_type:
        return {'error' : 'invalid_grant' }
    else:
        #the grant_type specified is not a valid one
        
        error_dict = dict([('error', 'invalid_grant')])
        
        return error_dict


def process_auth_code_grant(client_id,
                            client_secret,
                            scope,
                            code,
                            redirect_uri):
    client = get_client(client_id)

    print 'process_auth_code_grant redirect_uri', redirect_uri
    auth_code = db_get_auth_code(client_id,
                                 client_secret,
                                 code)
    print 'process_auth_code_grant', redirect_uri, client.redirect_uri
    if auth_code is not None and \
           client is not None and \
           redirect_uri == client.redirect_uri:
        access_token = create_access_token_from_code(auth_code)
        refresh_token = create_refresh_token_from_code(auth_code,
                                                       access_token)
        if not access_token:
            return  { 'error' : 'access_denied' }
        

        tokens = {
            'access_token'  : access_token,
            'token_type'    : 'bearer',
            'expires_in'    : get_token(client_id,
                                        client_secret,
                                        access_token).expire,
            'refresh_token' : refresh_token,
            }

        if scope:
            tokens.update({'scope'         : scope})

        return tokens
    

    
    #something went wrong
    return {'error' : 'invalid_client' }


def process_password_grant(client_id,
                           client_secret,
                           username,
                           password,
                           scope):
    access_token = create_access_token_from_user_pass(client_id,
                                                      client_secret,
                                                      username,
                                                      password,
                                                      scope)
    refresh_token = create_refresh_token_from_user_pass(client_id,
                                                        client_secret,
                                                        username,
                                                        password,
                                                        scope,
                                                        access_token)
    if access_token is not None and \
           refresh_token is not None:
        #turn it into a AccessToken instance & RefreshToken instance
        if client_id != None:
            access_token = get_token(client_id,
                                     client_secret,
                                     access_token)
            refresh_token = get_token(client_id,
                                      client_secret,
                                      refresh_token)
        else:
            access_token = get_token(username,
                                     password,
                                     access_token)
            refresh_token = get_token(username,
                                      password,
                                      refresh_token)
        logging.warn('access_token %s'% (access_token))
        tokens = {
            'access_token'  : access_token.code,
            'token_type'    : 'bearer',
            'expires_in'    : access_token.expire,
            'refresh_token' : refresh_token.code,
            }
        if scope:
            tokens.update({'scope'         : scope})

        return tokens

    #something went wrong
    return {'error' : 'invalid_client' }
    



def process_assertion_grant(client_id,
                            client_secret,
                            assertion_type,
                            assertion,
                            scope):
    #I'm not going to support this yet
    return { 'error' : 'invalid_grant' }




def process_refresh_token_grant(client_id,
                                client_secret,
                                refresh_token):

    print 'refresh_token'
    token = get_token(client_id, client_secret, refresh_token)
    if not isinstance(token, RefreshToken):
        return { 'error' : 'invalid_grant' }

    access_token = token.access_token
    delete_token(access_token)
    del access_token
    
    new_access_token = get_token(client_id,
                                 client_secret,
                                 create_access_token_from_refresh_token(token))

    tokens = {
        'access_token' : new_access_token.code,
        'token_type'   : 'bearer',
        'expires_in'   : new_access_token.expire,
        }

    if new_access_token.scope:
        tokens.update({'scope'        : new_access_token.scope})

    return tokens




def access_resource_authorised(token_str):
    '''
    attr token_str - the access token string representation
    
    returns the AccessToken object for the token string on success or the error message in the form of a python dictionary
    '''
    token = db_get_access_token(token_str)
    expired = available_scope = scope_list = True
    print 'access_resource_authorised', token
    if token:
        if token.scope == None or \
               token.scope != None and token.scope.lower() == 'all':
            return token
        elif token.scope != None and request.path_info in token.scope:
            return token
        else:
            return {'error':'insufficient_scope'}
    
    #assume to be a invalid token if it got this far
    return {'error':'invalid_token'}


@expose
@tools.response_headers(headers = [('Content-Type', 'image/svg')])
def avatar(access_token=None):
    token = access_resource_authorised(access_token)
    if isinstance(token, AccessToken):
        user = token.user
        
        try:
            with open('users/%s/avatar.svg' % (user.id)) as avatar:
                return avatar.read()
        except IOError, io:
            logging.warn(str(io))
            return None
            

    return str(token)

@expose
@tools.json_out()
def who_am_i(access_token=None):
    token = access_resource_authorised(access_token)
    if isinstance(token, AccessToken):
        user = token.user
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
        def index(self, error=None, code=None):
            if error != None:
                return "<html><head><title>Index</title></head><body><div>This is the index where a error %s occured</div></body></html>" % (error)
            elif code != None:
                data = {'grant_type': 'authorization_code',
                        'client_id': 'o9999o',
                        'client_secret': 'id',
                        'code': code,
                        'redirect_uri': 'http://localhost:8080',}
                request = Request('http://localhost:8080/token',
                                  urlencode(data))
                response = urlopen(request)
                message = response.read()
                return "<html><head><title>Index</title></head><body><div>This is the index where the code is %s</div><div>%s</div></body></html>" % (code, message)
            return "<html><head><title>Index</title></head><body><div>This is the index</div></body></html>"

    index = Root()

    index.authorise = authorise_client
    index.get_auth_code = get_auth_code
    index.token = get_access_token
    index.who_am_i = who_am_i
    index.avatar = avatar

    quickstart(index)
