"""
Carries out the responsiblity of authenticating
the client application/program and resource owner/user
"""

from cherrypy import expose, HTTPRedirect, config, tools
from Cheetah.Template import Template
from cStringIO import StringIO
from urllib import urlencode


from database import client_exists, get_client, \
     available_scope, get_password, get_user
from user_resource_grant import user_resource_grant


def check(username, password):
    if username in ('admin', 'james', 'jim',):
        return u"Invalid user"

    if 'password' != password:
        return u'Invalid password'
    

def login_required(func):

    def wrap(*args, **kwargs):
        return func(args, kwargs)

    return wrap

config.update({
    'tools.sessions.on': True,
    'tools.session_auth.on': True,
    'tools.session_auth.check_username_and_password':check,
    })              


@login_required
@expose
def authorise_client(response_type,
                     client_id,
                     redirect_uri,
                     scope = None,
                     state = None):
    if 'code' != response_type:
        #It can only be the value 'code'
        #redirect to redirect_uri
        #with error message as a parameter
        error_str = StringIO()
        error_str.write(redirect_uri)
        error_list = [('error', 'invalid_request')]
        if state != None:
            error_list.append(('state', state))
        error_str.write('?')
        error_str.write(urlencode(error_list))
        return HTTPRedirect(error_str.getvalue())


    if not client_exists(client_id):
        #client is not found in db
        error_str = StringIO()
        error_str.write(redirect_uri)
        error_list = [('error', 'invalid_client')]
        if state != None:
            error_list.append(('state', state))
        error_str.write('?')
        error_str.write(urlencode(error_list))
        return HTTPRedirect(error_str.getvalue())


    if scope != None:
        available = available_scope()
        scope_list = scope.split()
        available_scope = [x for x in scope_list if x in available]
        if available_scope != scope_list:
            #all the values in the scope
            #must match one in the available list
            error_str = StringIO()
            error_str.write(redirect_uri)
            error_list = [('error', 'invalid_scope')]
            if state != None:
                error_list.append(('state', state))
            error_str.write('?')
            error_str.write(urlencode(error_list))
            return HTTPRedirect(error_str.getvalue())


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
        return HTTPRedirect(error_str.getvalue())

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
        return HTTPRedirect(error_str.getvalue())

    
    grant = user_resource_grant()
    grant.client_id = client_id
    grant.user_id = user.id
    grant.redirect_uri = redirect_uri
    if scope:
        grant.scope = scope
        grant.message = "Allow %s to access to %s?" % (client.name, scope)
    else:
        grant.message = "Allow %s to access all your resources?" % (client.name)
        
    if state:
        grant.state = state

    grant.title = "Access grant"
    grant.action = "get_auth_code"

    
    return str(grant)



@expose
def get_auth_code(allow=None,
                  deny=None,
                  client_id=None,
                  redirect_uri=None,
                  scope=None,
                  state=None):
    if deny:
        error_str = StringIO()
        error_str.write(redirect_uri)
        error_list = [('error', 'access_denied')]
        if state != None:
            error_list.append(('state', state))
        error_str.write('?')
        error_str.write(urlencode(error_list))
        return HTTPRedirect(error_str.getvalue())
    elif allow:
        auth_code_str = create_auth_code(client_id, scope)
        response_str = StringIO()
        response_str.write(redirect_uri)
        response_list = [('code', auth_code_str)]
        if state:
            response_list.append(['state', state])
        response_str.write('?')
        response_str.write(urlencode(response_list))
        
        return HTTPRedirect(response_str.getvalue())


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
    
    auth_code = get_auth_code(client_id,
                              client_secret,
                              code)
    if auth_code is not None and \
           client is not None and \
           redirect_uri = client.redirect_uri:
        access_token = create_access_token_from_code(auth_code)
        refresh_token = create_refresh_token_from_code(auth_code)

        return {
            'access_token'  : access_token.code,
            'expires_in'    : access_token.expires,
            'refresh_token' : refresh_token.code,
            'scope'         : scope
            }

    
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
                                                        user_id,
                                                        password,
                                                        scope)
    if access_token is not None and \
           refresh_token is not None:
        return {
            'access_token'  : access_token.code,
            'expires_in'    : access_token.expires,
            'refresh_token' : refresh_token.code,
            'scope'         : scope
            }

    #something went wrong
    return {'error' : 'invalid_client' }
    



def process_assertion_grant(client_id,
                            client_secret,
                            assertion_type,
                            assertion,
                            scope):
    #I'm not going to support htis yet
    return { 'error' : 'invalid_grant' }




def process_refresh_token_grant(client_id,
                                client_secret,
                                refresh_token):
    
    token = get_token(client_id, client_secret, refresh_token)
    if not isinstance(token, RefreshToken):
        return { 'error' : 'invalid_grant' }

    access_token = token.access_token
    delete_token(access_token)
    del access_token
    
    new_access_token = create_access_token_from_refresh_token(token)

    return {
        'access_token' : new_access_token.code,
        'expires_in'   : new_access_token.expires,
        'scope'        : new_access_token.scope
        }
