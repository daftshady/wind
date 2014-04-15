"""

    wind.web.codec
    ~~~~~~~~~~~~~~

    Provides methods for string codec.

"""

from wind.compat import unicode

def encode(chunk, encoding='utf8'):
    """if chunk is unicode, encode chunk to specified encoding `utf8`.
    Should take `unicode` from compat because string is `unicode` by default
    in python 3.x

    """
    if chunk is not None:
        if isinstance(chunk, bytes):
            return chunk
        if isinstance(chunk, unicode):
            return chunk.encode(encoding)
