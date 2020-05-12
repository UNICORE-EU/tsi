"""
Contains functions to adapt the TSI to a site's local
policies

"""

def pre_become_user(user, config, LOG):
    """
    This function is invoked immediately before the TSI switches its user/group to
    perform some user-level action. Use it to adapt the environment, check constraints,
    check access policies, etc.

    WARNING: this code is executed with high privileges (typically root)

    This function returns an optional 'session info' object, that will be passed to the 
    post_become_user() function after the user-level function has executed.
    
    This function must throw an exception in case anything goes wrong
    and processing of the request should be aborted.

    """
    return None


def post_become_user(session_info, config, LOG):
    """
    This function is invoked immediately after the TSI switches its user/group to
    perform some action. Use it to adapt the environment, check constraints,
    check access policies, etc.

    This function returns no result.
    
    This function must throw an exception in case anything goes wrong
    and processing of the request should be aborted.

    """
    pass


def cleanup(session_info, config, LOG):
    """
    This function is invoked immediately before the TSI switches its user/group 
    back to the privileged user.

    This function returns no result.
    
    This function must throw an exception in case anything goes wrong
    and processing of the request should be aborted.

    """
    pass

