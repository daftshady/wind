"""

    wind.log
    ~~~~~~~~

    Simple logging system for wind

"""

import logging

from wind.exceptions import LoggerError


class LogType():
    """Logger name declarations"""
    BASE = 'wind'
    ACCESS = 'wind.access'


class LogLevel():
    """LogLevel based on python `logging`"""
    class Level(object):
        def __init__(self, method, code):
            self.method = method
            self.code = code
    INFO = Level('info', logging.INFO)
    WARN = Level('warn', logging.WARN)
    ERROR = Level('error', logging.ERROR)


class BaseLogger(object):
    """Wind base log class for general logging
    By default, streamHandler is attached to base, access logger.
    If you want to disable stream logging or change default level
    of this Logger(if needed), make custom `Logger` inheriting this class. 
    It is strongly advised you that you do not override constructor.
    
    Methods for the caller:

    - __init__(self)
    - set_format(format_, log_type)
    - attach_stream(log_type, log_level, format_=None)
    - attach_file(filename=None, format_=None, log_type=LogType.BASE)
    - log(msg, log_type=LogType.BASE, log_level=LogLevel.INFO)
    
    Methods that should not be overrided:
    - __init__(self)

    """
    def __init__(self): 
        """BaseLogger Initializer
        Should not be overrided.

        """
        self._base_logger = logging.getLogger(LogType.BASE)
        self._access_logger = logging.getLogger(LogType.ACCESS)
        self.initialize()

    def initialize(self):
        """Initialze hook.
        Should override this when you want to make custom logger

        """
        self._format = '[%(asctime)s]: %(message)s'
        self._date_format = '%Y-%m-%d %H:%M:%S'
        self._access_logger.setLevel(LogLevel.INFO.code)
        self.attach_stream(LogType.BASE, LogLevel.ERROR)
        self.attach_stream(LogType.ACCESS, LogLevel.INFO)
    
    # Public accessor declarations.
    @property
    def base(self):
        return self_base_logger

    @property
    def access(self):
        return self._access_logger
    
    @property
    def formatter(self):
        return logging.Formatter(self._format, self._date_format)

    def set_format(self, format_, log_type):
        """Change log format of specific logger
        :param format_: string configurated format following the form of
        python default logging library.
        ex) '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        """
        if not isinstance(format_, basestring):
            raise LoggerError('Invalid log formatter')
        self._format = format_
        self._logger(log_type).setFormatter(self.formatter)

    def attach_stream(self, log_type, log_level, format_=None):
        """Start printing logging output with standard stream.
        :param log_type: logger selector.
        :param log_level: log level for streamHandler. 
        This should be `LogLevel` object.(We are wrapping log level of
        python default logging library for the consistency of usage)
        """
        try:
            handler = logging.StreamHandler()
            handler.setLevel(log_level.code)
            formatter = logging.Formatter(format_) \
                if format_ is not None else self.formatter
            handler.setFormatter(formatter)
            logger = self._logger(log_type)
            logger.addHandler(handler)
        except (AttributeError, TypeError) as e:
            raise LoggerError(e)

    def attach_file(self, filename, format_=None, log_type=LogType.BASE):
        """Start file logging of specific logger.
        :param filename: logging file name.
        :param format_: file logging format. (optional)
        If not provided, it will use default log format of `BaseLogger`.
        :param log_type: log type for this file. (optional)
        By default, this method will attach file handler to base logger.

        """
        try:
            formatter = logging.Formatter(format_) \
                if format_ is not None else self.formatter
            file_handler = logging.FileHandler(filename)
            file_handler.setFormatter(formatter)
            logging.getLogger(log_type).addHandler(file_handler)
        except (AttributeError, TypeError) as e:
            raise LoggerError(e)
    
    def log(self, msg, log_type=LogType.BASE, log_level=LogLevel.INFO):
        """Log message to logger
        :param msg: actual log message.
        :param log_type: logger selector.
        By default, base logger will be selected.
        :param log_level: log level for this message.
        If `log_level` is lower than default level in logger, message may
        silently ignored.
        This should be `LogLevel` object.(We are wrapping log level of
        python default logging library for the consistency of usage)

        """
        logger = self._logger(log_type)
        if logger is not None:
            self._log_method(logger, log_level)(msg)

    def _logger(self, log_type):
        return self._base_logger \
            if log_type == LogType.BASE else self._access_logger

    def _log_method(self, logger, log_level):
        return getattr(logger, log_level.method)

wind_logger = BaseLogger()
