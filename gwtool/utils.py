import os
import sys
import time
import socket


single_instance_lock = None


def single_instance(name=__file__):
    """Ensure there is only one instance of this script running.
    """
    global single_instance_lock
    if single_instance_lock is not None:
        return

    while True:
        try:
            single_instance_lock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            single_instance_lock.bind('\0%s' % name)
            return
        except OSError as e:
            if e.errno == 98:  # 98: Address already in use
                time.sleep(0.1)
            else:
                raise e


def run_as_root():
    """Ensure this script is running with root user.
    """
    os.getuid() and os.execvp('sudo', ['sudo'] + sys.argv)


class cached_property:
    """
    Python prio to 3.8 does not implement cached_property, so we copied one from django:
    https://github.com/django/django/blob/4b146e0c83891fc67a422aa22f846bb7654c4d38/django/utils/functional.py#L7-L49

    Decorator that converts a method with a single self argument into a
    property cached on the instance.
    A cached property can be made out of an existing method:
    (e.g. ``url = cached_property(get_absolute_url)``).
    The optional ``name`` argument is obsolete as of Python 3.6 and will be
    deprecated in Django 4.0 (#30127).
    """
    name = None

    @staticmethod
    def func(instance):
        raise TypeError(
            'Cannot use cached_property instance without calling '
            '__set_name__() on it.'
        )

    def __init__(self, func, name=None):
        self.real_func = func
        self.__doc__ = getattr(func, '__doc__')

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name
            self.func = self.real_func
        elif name != self.name:
            raise TypeError(
                "Cannot assign the same cached_property to two different names "
                "(%r and %r)." % (self.name, name)
            )

    def __get__(self, instance, cls=None):
        """
        Call the function and put the return value in instance.__dict__ so that
        subsequent attribute access on the instance returns the cached value
        instead of calling cached_property.__get__().
        """
        if instance is None:
            return self
        res = instance.__dict__[self.name] = self.func(instance)
        return res
