# bcrypt 4.x compatibility with passlib
import bcrypt as _bcrypt
if not hasattr(_bcrypt, '__about__'):
    _bcrypt.__about__ = type('about', (), {'__version__': _bcrypt.__version__})
