import os
import sys
import time
import shlex
import shutil
import socket
import ipaddress
from pathlib import Path
from subprocess import call


DEVNULL = open(os.devnull, 'wb')
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


def xcall(command, **kwargs):
    from gwtool.env import logger

    logger.info(f'Call command: {" ".join(command)}')
    silence_error = kwargs.pop('silence_error', False)
    if silence_error:
        kwargs["stderr"] = DEVNULL
    ret = call(command, **kwargs)
    if ret != 0 and not silence_error:
        logger.error(f'ERROR: command exited with non-zero: {ret}')


def xrun(command):
    xcall(shlex.split(command))


def _gen_command(prefix):
    def _command(*args, **kwargs):
        command = prefix if isinstance(prefix, list) else shlex.split(prefix)
        for arg in args:
            command.extend(shlex.split(arg))
        xcall(command, **kwargs)
    return _command


ip = _gen_command('ip')
iproute = _gen_command('ip route')
iprule = _gen_command('ip rule')
ipxfrm = _gen_command('ip xfrm')
nft = _gen_command('nft')


def is_valid_cidr(address):
    try:
        ipaddress.ip_network(address, strict=False)
        return True
    except ValueError:
        return False


def copyfile(src, dst, create_dst_dir=True, backup=False):
    if not isinstance(src, Path):
        src = Path(src)
    if not isinstance(dst, Path):
        dst = Path(dst)

    if not src.exists():
        raise Exception(f'copyfile(): src does not exist: {src}')

    if src.is_dir():
        raise Exception(f'copyfile(): src must be a file, not directory: {src}')

    if dst.is_dir():
        dst = dst / src.name

    if not dst.parent.exists():
        print(f'create dst dir {dst.parent}')
        dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists():
        if backup:
            bak = dst.parent / (dst.name + '.bak')
            print(f'backup dst file: {dst} -> {bak}')
            copyfile(dst, bak)
        print(f'remove {dst}')
        dst.unlink()

    if dst.is_symlink() and not dst.exists():
        print(f'remove {dst}')
        dst.unlink()

    print(f'copy {src} -> {dst}')
    shutil.copyfile(src.as_posix(), dst.as_posix())
