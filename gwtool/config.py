import yaml
import ipaddress
from pathlib import Path

from gwtool.env import env, logger


class InterfaceConfig:
    """
    Interfaces can be discovered by pyroute2, however, we can provide more info on how to setup gateway.

    Currently the following properties can be configured:
    * devgroup: when invoking `ifaceup`, the interface devgroup will be set. Gwtool has 4 forcely defined groups,
                wan(1), lan(2), guest(3), tunnel(4). These 4 groups can be configured by name, others by number.
    * gateway: Gateway address of this interface. Some interfaces does not need gateway address, like ppp, tun, etc.
    """
    def __init__(self, name, devgroup=None, gateway=None, table=None, **kwargs):
        self.name = name

        # TODO Support user defined group names in /etc/iproute2/group
        devgroup = {'wan': 1, 'lan': 2, 'guest': 3, 'tunnel': 4}.get(devgroup, None)
        if not (devgroup is None or isinstance(devgroup, int)):
            logger.error(f'[InterfaceConfig] Invalid devgroup valud: {devgroup}')
            raise ValueError(f'Invalid devgroup value: {devgroup}')
        self.devgroup = devgroup

        # Gateway address must be valid ip address (not cidr).
        # ip_address() supports both v4 and v6, however we currently only consider v6.
        if gateway:
            try:
                ipaddress.ip_address(gateway)
            except ipaddress.AddressValueError:
                logger.error(f'[InterfaceConfig] Invalid gateway value (must be valid ip address): {gateway}')
                raise
        self.gateway = gateway

    def validate(self, **kwargs):
        return True


class GatewayConfig:
    """
    A gateway is a next hop used in route entry. Gwtool creates gateway intances automatically from interfaces,
    addition to that, user can define custom gateways or change how interface gateway work.

    The following properties can be used:
    * link: indicates this gateway is alias of another gateway. It can be useful for making route table reads clear.
    * interface: if this gateway consists of only one interface, configure it via this property. If interface name
      is same as gateway name, it can be omitted.
    * interfaces: if this gateway consists of more than one interfaces, config via this property. This property
      conflicts with interface, you should only use one of them.
    * gateway: for single interface gateway, we can override gateway address defined on the interface.
    """
    def __init__(self, name, link=None, interface=None, interfaces=None, gateway=None, **kwargs):
        self.name = name

        # TODO should check if the link name exists
        self.link = link

        if interface and interfaces:
            logger.error('[GatewayConfigure] interface and interfaces are exclusive')
            raise ValueError('"interface" and "interfaces" can not be used together')
        if gateway and interfaces:
            logger.error('[GatewayConfigure] interface and interfaces are exclusive')
            raise ValueError('"gateway" and "interfaces" can not be used together')

        # TODO should check if interface exists
        if interfaces:
            self.single_interface_mode = False
            self.interfaces = interfaces
        else:
            self.single_interface_mode = True
            self.interface = interface or name
            self.gateway = gateway

    def validate(self, *, gateways, interfaces, **kwargs):
        # TODO
        return True


class RouteTableConfig:
    """
    Custom route tables.
    """
    def __init__(self, table, entries, **kwargs):
        self.table = table
        self.entries = entries

    def validate(self, *, netzones, **kwargs):
        # TODO
        return True


class RouteRuleConfig:
    """
    Custom route rules.
    """
    def __init__(self, rule, **kwargs):
        self.rule = rule

    def validate(self, **kwargs):
        return True


class Config:
    """
    Represents the whole gateway.yaml config file
    """
    def __init__(self, config_file):
        if config_file.exists():
            logger.info(f'Loading gateway config file: {config_file}')
            try:
                with config_file.open(encoding='utf8') as fp:
                    content = yaml.safe_load(fp)
            except Exception:
                logger.error(f'Error loading gateway config file: {config_file}')
                raise
        else:
            logger.info(f'Config file does not exist: {config_file}, assume empty config')
            content = {}

        self.interfaces = {}
        for name, config in content.get('interfaces', {}).items():
            self.interfaces[name] = InterfaceConfig(name, **config)

        self.gateways = {}
        for name, config in content.get('gateways', {}).items():
            self.gateways[name] = GatewayConfig(name, **config)

        self.route_tables = {}
        for table, entries in content.get('routing', {}).get('tables', {}).items():
            self.route_tables[table] = RouteTableConfig(table, entries)

        self.route_rules = []
        for rule in content.get('routing', {}).get('rules', []):
            self.route_rules.append(RouteRuleConfig(rule=rule))

        netzone_search_path = []
        paths = content.get('netzone_search_path', [])
        if not isinstance(paths, list):
            logger.error('Config Error: netzone_search_path must be list of paths')
            raise ValueError('Invalid netzone_search_path, must be list of paths')
        for path in paths:
            netzone_search_path.append(Path(path))
        netzone_search_path.append(env.codespace / 'netzones')
        self.netzone_search_path = netzone_search_path

    def validate(self, **kwargs):
        for interface in self.interfaces.values():
            interface.validate(**kwargs)
        for gateway in self.gateways.values():
            gateway.validate(**kwargs)
        for table in self.route_tables.values():
            table.validate(**kwargs)
        for rule in self.route_rules.valus():
            rule.validate(**kwargs)
