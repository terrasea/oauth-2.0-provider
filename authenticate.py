"""
Carries out the responsiblity of authenticating
the client application/program and resource owner/user
"""

from cherrypy import expose, HTTPRedirect, config
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

