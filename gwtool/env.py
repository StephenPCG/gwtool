import sys
import logging
import logging.handlers
from pathlib import Path

from gwtool.utils import cached_property


class NotConfigured:
    pass


class Env:
    """
    Env holds some global variables for paths.
    """
    def __init__(self):
        self._configured = False

        self._workspace = NotConfigured
        self._config_file = NotConfigured
        self._log_file = NotConfigured

        self.logger = logging.getLogger(self.cmdline_name)
        self.logger.setLevel(logging.INFO)

        if self.is_interactive:
            self._add_log_stream()

    def configure(self, *, workspace=None, config_file=None, log_file=None):
        if self._configured:
            raise Exception('Env already configured.')

        if workspace:
            self._workspace = Path(workspace)
        if config_file:
            self._config_file = Path(config_file)
        if log_file:
            self._log_file = Path(log_file)

        # we have configured, so let's enable file logging
        self._add_log_file(self.log_file)

        self._configured = True

    @cached_property
    def codespace(self):
        """
        Codespace is where this code lived, we have some builtin data stored here (e.g. netzone files).
        """
        return Path(__file__).parent

    @property
    def workspace(self):
        """
        Workspace stores instance configuration and scripts. It usually is '/opt/gateway'.
        """
        if self._workspace is NotConfigured:
            return Path('/opt/gateway')
        return self._workspace

    @property
    def config_file(self):
        """
        Config file is the core configuration to gwtool. It usually is {workspace}/gateway.yaml.
        """
        if self._config_file is NotConfigured:
            return self.workspace / 'gateway.yaml'
        return self._config_file

    @property
    def log_file(self):
        """
        Gwtool is usually run by triggers (e.g. if-up), we try to log important messages for trouble shooting.
        """
        if self._log_file is NotConfigured:
            return self.workspace / 'var/log/gwtool.log'
        return self._log_file

    @cached_property
    def is_interactive(self):
        """
        Where currently is running interactively (script is invoked manually) or in backend (invoked by triggers).
        """
        return sys.stdout.isatty()

    @cached_property
    def cmdline_name(self):
        """
        The command line name, used by logger name.
        """
        if sys.argv[0] in ['python', 'python3', 'ipython', 'ipython3']:
            return 'shell'
        return Path(sys.argv[0]).stem

    @cached_property
    def log_format(self):
        return '[%(asctime)s][%(name)s][%(levelname)s]: %(message)s'

    def _add_log_stream(self):
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(self.log_format))

        self.logger.addHandler(handler)

    def _add_log_file(self, logfile):
        logdir = logfile.parent
        if not logdir.exists():
            logdir.mkdir(parents=True, exist_ok=True)

        handler = logging.handlers.TimedRotatingFileHandler(filename=logfile, when='W0', encoding='utf8')
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(self.log_format))

        self.logger.addHandler(handler)


env = Env()
logger = env.logger


__ALL__ = [
    'env',
    'logger',
]
