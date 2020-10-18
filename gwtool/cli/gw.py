import os
import sys
import click
import socket
import logging
from pathlib import Path

from gwtool.utils import run_as_root, single_instance, copyfile, xrun
from gwtool.env import env
from gwtool import libgw


@click.group('cli')
def cli():
    # if platform is not linux, run_as_root(), single_instance() will fail.
    if sys.platform != 'linux':
        raise Exception('This script can only be run on linux.')

    run_as_root()
    single_instance()

    fqdn = socket.getfqdn()
    if 'gateway' not in fqdn:
        # we're not on a gateway, may be just debugging the script
        env.configure(workspace=Path(os.getcwd()) / 'example/')
        env.logger.setLevel(logging.DEBUG)
        env.logger.info(f'Running: {" ".join(sys.argv)}')
        env.logger.warning('Not on a gateway box.')
        # loading gateway resources, will fail
        libgw.load()
    else:
        # TODO, use env variables or cli args for env config
        env.configure()
        env.logger.setLevel(logging.INFO)
        env.logger.info(f'Running: {" ".join(sys.argv)}')
        # loading gateway resources
        libgw.load()


@cli.group('setup', invoke_without_command=True)
@click.pass_context
def cli_setup(ctx):
    if ctx.invoked_subcommand is None:
        from .setup import setup_all
        setup_all()


@cli_setup.command('firewall')
def cli_setup_firewall():
    from .setup import setup_firewall, setup_route
    setup_firewall()
    setup_route()


@cli_setup.command('route')
def cli_setup_route():
    from .setup import setup_route
    setup_route()


@cli_setup.command('portmap')
def cli_setup_portmap():
    from .setup import setup_portmap
    setup_portmap()


@cli_setup.command('ifaces')
def cli_setup_ifaces():
    from .setup import setup_ifaces
    setup_ifaces()


@cli.group('install')
def install():
    pass


@install.command('coredns')
def install_coredns():
    datadir = env.codespace / 'install' / 'coredns'
    corefile = env.workspace / 'configs' / 'Corefile'

    copyfile(datadir / 'coredns.bin', '/usr/local/bin/coredns')
    copyfile(datadir / 'coredns-sysusers.conf', '/usr/lib/sysusers.d/coredns.conf')
    copyfile(datadir / 'coredns-tmpfiles.conf', '/usr/lib/tmpfiles.d/coredns.conf')
    copyfile(datadir / 'coredns.service', '/etc/systemd/system/coredns.service')
    copyfile(datadir / 'Corefile', corefile, backup=True)
    xrun(f'ln -snf {corefile} /etc/coredns/Corefile')
    xrun('systemd-sysusers')
    xrun('systemd-tmpfiles --create')
    xrun('systemctl daemon-reload')
    xrun('systemctl enable --now coredns')


@install.command('vlmcsd')
def install_vlmcsd():
    datadir = env.codespace / 'install' / 'vlmcsd'

    copyfile(datadir / 'vlmcsd.bin', '/usr/local/bin/vlmcsd')
    copyfile(datadir / 'vlmcsd-sysusers.conf', '/usr/lib/sysusers.d/vlmcsd.conf')
    copyfile(datadir / 'vlmcsd-tmpfiles.conf', '/usr/lib/tmpfiles.d/vlmcsd.conf')
    copyfile(datadir / 'vlmcsd.service', '/etc/systemd/system/vlmcsd.service')
    xrun('systemd-sysusers')
    xrun('systemd-tmpfiles --create')
    xrun('systemctl daemon-reload')
    xrun('systemctl enable --now vlmcsd')


@install.command('dnsmasq')
def install_dnsmasq():
    datadir = env.codespace / 'install' / 'dnsmasq'
    targetdir = env.workspace / 'dnsmasq'

    if not Path('/var/lib/dpkg/info/dnsmasq.list').exists():
        xrun('apt-get install -y --no-install-recommends dnsmasq')

    xrun('sed -i "/--local-service/s/^/#/" /etc/init.d/dnsmasq')

    copyfile(datadir / 'dnsmasq.conf', targetdir / 'dnsmasq.conf', backup=True)
    copyfile(datadir / 'conf.d/china-114.conf', targetdir / 'conf.d/china-114.conf')
    copyfile(datadir / 'conf.d/china-223.conf', targetdir / 'conf.d/china-223.conf')
    copyfile(datadir / 'apple.china.conf', targetdir / 'conf.d/apple.china.conf')
    copyfile(datadir / 'google.china.conf', targetdir / 'conf.d/google.china.conf')
    copyfile(datadir / 'bogus-nxdomain.china.conf', targetdir / 'conf.d/bogus-nxdomain.china.conf')
    xrun(f'ln -snf {datadir / "dnsmasq.conf"} /etc/dnsmasq.conf')

    Path('/var/log/dnsmasq').mkdir(parents=True, exists_ok=True)
    copyfile(datadir / 'dnsmasq.logrotate.conf', '/etc/logrotate.d/dnsmasq')

    xrun('systemctl enable dnsmasq')
    xrun('systemctl restart dnsmasq')


@install.command('sysctl')
def install_sysctl():
    copyfile(env.codespace / 'install/sysctl/99-gateway.conf', '/etc/sysctl.d/99-gateway.conf')


@install.command('collectd')
def install_collectd():
    datadir = env.codespace / 'install' / 'collectd'
    collectd_config_file = env.workspace / 'configs' / 'collectd.conf'

    if not Path('/var/lib/dpkg/info/collectd.list').exists():
        xrun('apt-get install -y --no-install-recommends collectd liboping0')

    copyfile(datadir / 'collectd.conf', collectd_config_file, backup=True)
    xrun(f'ln -snf {collectd_config_file} /etc/collectd/collectd.conf')

    xrun('systemctl enable collectd')
    xrun('systemctl restart collectd')
