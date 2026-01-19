import logging
log = logging.getLogger( __name__ )

def restrict_testing_tools_to_admins( context, tool ):
    """
    This tool filter will hide the upload tool from all users except admin
    users. This can be enabled by renaming this file to examples.py and adding
    the following to the ``app:main`` section of ``galaxy.ini``:

        tool_filters = examples:restrict_testing_tools_to_admins
    """
    if tool.id == "testing_html" or tool.id == "testing_pbs" or tool.id == "testing":
        return context.trans.user_is_admin
    return True
