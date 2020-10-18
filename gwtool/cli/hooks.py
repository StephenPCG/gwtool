import os
import sys

from gwtool.env import env, logger
from gwtool import libgw
from gwtool.utils import xcall


def ifaceup():
    env.configure()
    logger.info(f'Running: {" ".join(sys.argv)}')
    libgw.load()

    if os.environ.get('IFACE'):
        ifname = os.environ['IFACE']
    elif len(sys.argv) >= 2:
        ifname = sys.argv[1]
    else:
        return

    iface = libgw.Interface.get(ifname)
    if not iface or not iface.exists:
        logger.error(f'iface does not found in libgw: {ifname}')
        return

    if iface.config and iface.config.devgroup:
        logger.info(f'setting iface group, iface={ifname} group={iface.config.devgroup}')
        xcall(['ip', 'link', 'set', 'dev', ifname, 'group', str(iface.config.devgroup)])

    from .setup import setup_firewall, setup_route
    setup_firewall()
    setup_route()
