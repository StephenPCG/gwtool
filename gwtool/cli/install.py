import sys
import click
import shutil
from pathlib import Path

from gwtool.env import env, logger
from gwtool.utils import run_as_root, single_instance, xrun


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
        logger.info(f'create dst dir {dst.parent}')
        dst.parent.mkdir(parents=True, exists_ok=True)

    if dst.exists():
        if backup:
            bak = dst.parent / (dst.name + '.bak')
            logger.info(f'backup dst file: {dst} -> {bak}')
            copyfile(dst, bak)
        logger.info(f'remove {dst}')
        dst.unlink()

    logger.info(f'copy {src} -> {dst}')
    shutil.copyfile(src.as_posix(), dst.as_posix())


@click.group('cli')
def install():
    run_as_root()
    single_instance()
    env.configure()
    env.logger.info(f'Running: {" ".join(sys.argv)}')


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
    xrun('systemctl daemon-reload')
    xrun('systemctl enable --now coredns')


@install.command('vlmcsd')
def install_vlmcsd():
    datadir = env.codespace / 'install' / 'vlmcsd'

    copyfile(datadir / 'vlmcsd.bin', '/usr/local/bin/vlmcsd')
    copyfile(datadir / 'vlmcsd-sysusers.conf', '/usr/lib/sysusers.d/vlmcsd.conf')
    copyfile(datadir / 'vlmcsd-tmpfiles.conf', '/usr/lib/tmpfiles.d/vlmcsd.conf')
    copyfile(datadir / 'vlmcsd.service', '/etc/systemd/system/vlmcsd.service')
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
