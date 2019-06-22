import utime
import sys
import uio
import usocket

CRITICAL = 50
ERROR    = 40
WARNING  = 30
INFO     = 20
DEBUG    = 10
LLDEBUG  = 5
NOTSET   = 0

_level_dict = {
    CRITICAL: "CRITICAL",
    ERROR: "ERROR",
    WARNING: "WARNING",
    INFO: "INFO",
    DEBUG: "DEBUG",
    LLDEBUG: "LLDEBUG",
}

def addLevelName(level, name):
    _level_dict[level] = name

class Logger:

    level = NOTSET

    def __init__(self, name):
        self.name = name
        self.handlers = None

    def _level_str(self, level):
        l = _level_dict.get(level)
        if l is not None:
            return l
        return "LVL%s" % level

    def setLevel(self, level):
        self.level = level

    def isEnabledFor(self, level):
        return level >= (self.level or _level)

    def log(self, level, msg, *args, module=None):
        if level >= (self.level or _level):
            record = LogRecord(
                self.name, level, None, None, msg, args, None, None, None, module=module
            )

            if self.handlers:
                for hdlr in self.handlers:
                    hdlr.handle(record)

    def lldebug(self, msg, *args, module=None):
        self.log(LLDEBUG, msg, *args, module=module)

    def debug(self, msg, *args, module=None):
        self.log(DEBUG, msg, *args, module=module)

    def info(self, msg, *args, module=None):
        self.log(INFO, msg, *args, module=module)

    def warning(self, msg, *args, module=None):
        self.log(WARNING, msg, *args, module=module)

    warn = warning

    def error(self, msg, *args, module=None):
        self.log(ERROR, msg, *args, module=module)

    def critical(self, msg, *args, module=None):
        self.log(CRITICAL, msg, *args, module=module)

    def exc(self, e, msg, *args, module=None):
        buf = uio.StringIO()
        sys.print_exception(e, buf)
        self.log(ERROR, msg + "\n" + buf.getvalue(), *args, module=module)

    def exception(self, msg, *args, module=None):
        self.exc(sys.exc_info()[1], msg, *args, module=module)

    def addHandler(self, hdlr):
        if self.handlers is None:
            self.handlers = []
        self.handlers.append(hdlr)


_level = INFO
_loggers = {}


def getLogger(name=None):
    if name is None:
        name = "root"
    if name in _loggers:
        return _loggers[name]
    if name == "root":
        l = Logger(name)
        sh = StreamHandler()
        sh.formatter = Formatter()
        l.addHandler(sh)
    else:
        l = Logger(name)
    _loggers[name] = l
    return l

def info(msg, *args, module=None):
    getLogger(None).info(msg, *args, module=module)

def debug(msg, *args, module=None):
    getLogger(None).debug(msg, *args, module=module)

def warning(msg, *args):
    getLogger(None).warning(msg, *args)

warn = warning

def error(msg, *args):
    getLogger(None).error(msg, *args)

def critical(msg, *args):
    getLogger(None).critical(msg, *args)

def exception(msg, *args):
    getLogger(None).exception(msg, *args)

def basicConfig(level=INFO, filename=None, stream=None, format=None, style="%"):
    global _level
    _level = level
    if filename:
        h = FileHandler(filename)
    else:
        h = StreamHandler(stream)
    h.setFormatter(Formatter(format, style=style))
    root.handlers.clear()
    root.addHandler(h)


class Handler:
    def __init__(self, formatter=None, level=NOTSET):
        self.formatter = formatter or Formatter()
        self.level = level

    def setFormatter(self, fmt):
        self.formatter = fmt

    def setLevel(self, level):
        self.level = level

    def handle(self, record):
        if record.levelno >= (self.level or _level):
            self.emit(record)

    def emit(self, record):
        raise NotImplementedError('emit must be implemented'
                                  'by Handler subclasses')


class StreamHandler(Handler):
    def __init__(self, *args, stream=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._stream = stream or sys.stderr
        self.terminator = "\n"

    def emit(self, record):
        self._stream.write(self.formatter.format(record) + self.terminator)

    def flush(self):
        pass


class FileHandler(Handler):
    def __init__(self, filename, *args, mode="a", encoding=None,
                 delay=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.encoding = encoding
        self.mode = mode
        self.delay = delay
        self.terminator = "\n"
        self.filename = filename

        self._f = None
        if not delay:
            self._f = open(self.filename, self.mode)

    def emit(self, record):
        if self._f is None:
            self._f = open(self.filename, self.mode)

        self._f.write(self.formatter.format(record) + self.terminator)
        self._f.flush()

    def close(self):
        if self._f is not None:
            self._f.close()

class UDPHandler(Handler):
    def __init__(self, addr, *args, port=4445, **kwargs):
        super().__init__(*args, **kwargs)
        self._sock = usocket.socket(usocket.AF_INET, usocket.SOCK_DGRAM)
        self._addr = usocket.getaddrinfo(addr, port)[0][-1]
        self.terminator = "\n"

    def emit(self, record):
        self._sock.sendto(self.formatter.format(record) + self.terminator,
                          self._addr)

    def close(self):
        if self._sock is not None:
            self._sock.close()


class Formatter:

    def __init__(self, fmt=None, datefmt=None, style="%", converter=None):
        self.fmt = fmt or "%(message)s"
        self.datefmt = datefmt or "{0}-{1}-{2} {3}:{4}:{5}"
        self.converter = converter or utime.localtime

        if style not in ("%", "{"):
            raise ValueError("Style must be one of: %, {")

        self.style = style

    def usesTime(self):
        if self.style == "%":
            return "%(asctime)" in self.fmt
        elif self.style == "{":
            return "{asctime" in self.fmt

    def format(self, record):
        # The message attribute of the record is computed using msg % args.
        record.message = record.msg % record.args

        # If the formatting string contains '(asctime)', formatTime() is called to
        # format the event time.
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        # If there is exception information, it is formatted using formatException()
        # and appended to the message. The formatted exception information is cached
        # in attribute exc_text.
        if record.exc_info is not None:
            record.exc_text += self.formatException(record.exc_info)
            record.message += "\n" + record.exc_text

        # The record’s attribute dictionary is used as the operand to a string
        # formatting operation.
        if self.style == "%":
            return self.fmt % record.__dict__
        elif self.style == "{":
            return self.fmt.format(**record.__dict__)
        else:
            raise ValueError(
                "Style {0} is not supported by logging.".format(self.style)
            )

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        return datefmt.format(*ct)

    def formatException(self, exc_info):
        raise NotImplementedError()

    def formatStack(self, stack_info):
        raise NotImplementedError()


root = getLogger()


class LogRecord:
    def __init__(
        self, name, level, pathname, lineno, msg, args, exc_info, func=None,
        sinfo=None, module=None
    ):
        ct = utime.time()
        self.created = ct
        self.msecs = (ct - int(ct)) * 1000
        self.name = name
        self.levelno = level
        self.levelname = _level_dict.get(level, None)
        self.pathname = pathname
        self.lineno = lineno
        self.msg = msg
        self.args = args
        self.exc_info = exc_info
        self.func = func
        self.sinfo = sinfo
        self.module = module or '<?>'
