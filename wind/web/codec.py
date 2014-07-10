"""

    wind.web.codec
    ~~~~~~~~~~~~~~

    Provides methods for string codec.

"""

from wind.exceptions import CodecError
from wind.compat import unicode, is_py3

_DEFAULT_ENCODING = 'utf8'


def encode(chunk, encoding=_DEFAULT_ENCODING):
    """if chunk is unicode, encode chunk to specified encoding `utf8`.
    Should take `unicode` from compat because string is `unicode` by default
    in python 3.x
    NOTE that if chunk is `int`, it will be converted to str and encoded.

    """
    if chunk is not None:
        if isinstance(chunk, int):
            chunk = str(chunk)

        if isinstance(chunk, bytes):
            return chunk
        if isinstance(chunk, unicode):
            return chunk.encode(encoding)


def to_str(bytes_):
    """Converts bytes to str in some iteratable object or `bytes`.
    This method only accept params with type `tuple`, `list`, `bytes`
    and returns bytes decoded object.

    """
    if not is_py3 or isinstance(bytes_, str):
        return bytes_

    if isinstance(bytes_, (tuple, list)):
        return type(bytes_)(i.decode(_DEFAULT_ENCODING) for i in bytes_)
    if isinstance(bytes_, bytes):
        return bytes_.decode(_DEFAULT_ENCODING)
    raise CodecError('`bytes_to_str` only accepts `tuple`, `list`, `bytes`.')


def decode_dict(dict_):
    """Let k, v pairs of `dict` to be decoded by `to_str` method.
    This method returnes newly created `dict` with k, v decoded."""
    if not is_py3:
        return dict_
    if not isinstance(dict_, dict):
        raise CodecError('`encode_dict` only accepts `dict`')

    return dict(to_str(i) for i in dict_.items())
