"""

    wind.compat
    ~~~~~~~~~~~

    Python 2.x and 3.x compatibility.

"""

import sys

ver = sys.version_info

is_py2 = (ver[0] == 2)
is_py3 = (ver[0] == 3)

if is_py2:
    basestring = basestring
    from urlparse import urlparse, parse_qsl


elif is_py3:
    basestring = (str, bytes)
    from urllib.parse import urlparse, parse_qsl
