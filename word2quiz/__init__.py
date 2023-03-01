""" init """
__version__ = '0.1.14'
from .main import parse
from .main import parse_document_d2p
from .main import word2quiz
from .main import get_document_html
from .main import normalize_size
from canvasrobot import CanvasRobot, UpdateDatabaseThread

# The __all__ attribute defines the items exported from statement,
# 'from [name] import *', but also to say, "This is the public API".
__all__ = ('CanvasRobot', 'UpdateDatabaseThread' ,'parse', 'parse_document_d2p', 'word2quiz', 'get_document_html', 'normalize_size')