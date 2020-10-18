import sys
import logging
import logging.handlers
from pathlib import Path

from gwtool.utils import cached_property


class Env:
    """
    Env holds some global variables for paths.
    """
    def __init__(self):
        self._configured = False

        # Codespace is where this code lived, we have some builtin data stored here (e.g. netzone files).
        self.codespace = Path(__file__).parent

        if sys.argv[0] in ['python', 'python3', 'ipython', 'ipython3']:
            logger_name = 'shell'
        else:
            logger_name = Path(sys.argv[0]).stem

        self._log_format = '[%(asctime)s][%(name)s][%(levelname)s]: %(message)s'
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        # if running interactively, add stream handler to logger
        if sys.stdout.isatty():
            self._add_log_stream()

    def configure(self, *, workspace=None, config_file=None, log_file=None):
        if self._configured:
            raise Exception('Env already configured.')

        # Workspace stores instance configuration and scripts. It usually is '/opt/gateway'.
        self.workspace = Path(workspace or '/opt/gateway')
        # Config file is the core configuration to gwtool. It usually is {workspace}/configs/gateway.yaml.
        self.config_file = config_file and Path(config_file) or self.workspace / 'configs' / 'gateway.yaml'
        # Gwtool is usually run by triggers (e.g. if-up), we try to log important messages for trouble shooting.
        self.log_file = log_file and Path(log_file) or self.workspace / 'var/log/gwtool.log'

        # we have configured, so let's enable file logging
        self._add_log_file(self.log_file)

        self._configured = True

    @cached_property
    def gwconfig(self):
        if not self._configured:
            raise Exception('Env not configured, can not access gwconfig.')

        from gwtool.config import Config
        return Config(self.config_file)

    def _add_log_stream(self):
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(self._log_format))

        self.logger.addHandler(handler)

    def _add_log_file(self, logfile):
        logdir = logfile.parent
        if not logdir.exists():
            logdir.mkdir(parents=True, exist_ok=True)

        handler = logging.handlers.TimedRotatingFileHandler(filename=logfile, when='W0', encoding='utf8')
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(self._log_format))

        self.logger.addHandler(handler)


env = Env()
logger = env.logger


__ALL__ = [
    'env',
    'logger',
]
