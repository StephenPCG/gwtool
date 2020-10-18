import tempfile

from gwtool.env import env, logger
from gwtool.utils import is_valid_cidr, xcall, xrun, iprule, iproute
from gwtool.libgw import Gateway, NetZone


def setup_firewall():
    logger.info('running setup_firewall()')
    script = env.gwconfig.firewall_script or env.codespace / 'nftables' / 'firewall.nft'
    # run "nft -f {script}", in case firewall_script has no exec bit set
    xrun(f'/usr/sbin/nft -f {script}')


def setup_route():
    logger.info('running setup_route()')
    # create user defined tables
    for table in env.gwconfig.route_tables.values():
        create_route_table(table.table, table.entries)

    # delete default route in table main
    iproute('delete default table main', silence_error=True)

    # flush ip rules
    flush_iprule()
    iprule('add from all lookup main pref 50')

    # apply user defined rules
    for rr in env.gwconfig.route_rules:
        iprule(f'add {rr.rule}')


def setup_portmap():
    logger.info('running setup_portmap()')
    logger.warning('setup_portmap() is not implemented')
    # TODO only flush and re-setup portmap rules
    pass


def setup_ifaces():
    logger.info('running setup_ifaces()')
    logger.warning('setup_ifaces() is not implemented')
    # TODO find all user configured links and setup devgroup
    # this is only useful for fixing up links when ifaceup is not run when link went up
    pass


def setup_all():
    setup_ifaces()
    setup_firewall()
    setup_route()


def flush_iprule():
    iprule('flush')
    iprule('add from all lookup main pref 32766')
    iprule('add from all lookup default pref 32767')


def create_route_table(table, entries):
    iproute(f'flush table {table}')

    lines = []
    for (target, gateway_name) in entries:
        gateway = Gateway.get(gateway_name)
        if not gateway:
            logger.error(f'invalid gateway in route table {table}: {gateway_name}, rule skipped')
            continue

        if not gateway.available:
            logger.error(f'gateway is not available: {gateway_name}, rule skipped')
            continue

        if is_valid_cidr(target):
            iproute(f'replace table {table} {target} {gateway.gwdef}')
            continue

        zone = NetZone.get(target)
        if not zone:
            logger.error(f'invalid target in route table {table}: {target}, rule skipped')
            continue

        for prefix in zone.cidr_list:
            lines.append(f'route replace table {table} {prefix} {gateway.gwdef}\n')

    if not lines:
        logger.warning(f'No rules for table: {table}')
        return

    with tempfile.NamedTemporaryFile() as f:
        f.write(''.join(lines).encode('ascii'))
        f.flush()
        xcall(['ip', '-batch', '-'], stdin=open(f.name))
