import re
from pyroute2 import IPRoute

from gwtool.utils import cached_property
from gwtool.env import env, logger


class Interface:
    def __init__(self, ifname, link, config=None):
        self.ifname = ifname
        self.link = link
        self.config = config
        logger.debug(f'Loaded interface: {self}')

    @cached_property
    def user_configured(self):
        """
        If user provided configuration for this interface.
        """
        return self.config is not None

    @cached_property
    def exists(self):
        """
        If this interfaces exists in os
        """
        return self.link is not None

    @cached_property
    def index(self):
        return self.link and self.link['index']

    @cached_property
    def devgroup(self):
        return self.link and self.link.get_attr('IFLA_GROUP')

    @cached_property
    def operstate(self):
        return self.link and self.link.get_attr('IFLA_OPERSTATE')

    @cached_property
    def link_kind(self):
        # bridge, vlan, tun, tap, gre, ppp, wireguard, ...
        return self.link and self.link.get_nested('IFLA_LINKINFO', 'IFLA_INFO_KIND')

    def get_gwdef(self, gateway=None):
        if not gateway:
            gateway = self.config and self.config.gateway
        if gateway:
            return f'via {gateway} dev {self.ifname}'
        else:
            return f'dev {self.ifname}'

    # ---- 8< ----

    _interfaces = {}
    _loaded = False

    def __str__(self):
        config = self.user_configured and 'yes' or 'no'
        return f'<Interface ifname={self.ifname} index={self.index} operstate={self.operstate} config={config}>'

    __repr__ = __str__

    @classmethod
    def _load_interfaces(cls):
        if cls._loaded:
            return

        # scan all interfaces in os
        with IPRoute() as ipr:
            for link in ipr.get_links():
                ifname = link.get_attr('IFLA_IFNAME')
                config = env.gwconfig.interfaces.get(ifname, None)
                cls._interfaces[ifname] = cls(ifname, link, config)

        # scan all user configured interface and register as well
        for ifname, config in env.gwconfig.interfaces.items():
            logger.warning(f'Link not found for user configured interface: {ifname}')
            if ifname not in cls._interfaces:
                cls._interfaces[ifname] = cls(ifname, None, config)

        cls._loaded = True

    @classmethod
    def get(cls, ifname):
        if not cls._loaded:
            raise Exception('Interfaces not loaded, please load interfaces before using get()')
        return cls._interfaces.get(ifname)


class Gateway:
    def __init__(self, name, config=None):
        self.name = name
        self.config = config

        config = config and 'yes' or 'no'
        # Can not access self.__str__() now, it requires all gateway loaded (so links can be resolved)
        logger.debug(f'Loaded gateway: <Gateway name={self.name} config={config}>')

    @cached_property
    def user_configured(self):
        return self.config is not None

    @cached_property
    def single_interface_mode(self):
        return not self.config or self.config.single_interface_mode

    @cached_property
    def link(self):
        if self.config and self.config.link:
            return self.__class__.get(self.config.link)

    @cached_property
    def interfaces(self):
        if self.link:
            return self.link.interfaces

        if self.single_interface_mode:
            raise AttributeError('Gateway contains only one interface')

        interfaces = []
        for ifname in self.config.interfaces:
            interfaces.append(Interface.get(ifname))
        return interfaces

    @cached_property
    def interface(self):
        if self.link:
            return self.link.interface

        if not self.single_interface_mode:
            raise AttributeError('Gateway contains multiple interfaces')

        ifname = self.config and self.config.interface or self.name
        return Interface.get(ifname)

    @cached_property
    def available(self):
        if self.link:
            return self.link.available

        if self.single_interface_mode:
            # XXX self.interface should never be none if we called gateway.validate()
            return self.interface.exists
        else:
            # XXX self.interfaces should never contain none if we called gateway.validate()
            return all([iface.exists for iface in self.interfaces])

    @cached_property
    def gwdef(self):
        if self.link:
            return self.link.gwdef

        if self.single_interface_mode:
            return self.interface.get_gwdef(self.config and self.config.gateway)

        return ' '.join([f'nexthop {iface.get_gwdef()}' for iface in self.interfaces])

    # ---- 8< ----

    _gateways = {}
    _loaded = False

    def __str__(self):
        if self.single_interface_mode:
            ifstr = f'interface={self.interface.ifname}'
        else:
            ifstr = f'interfaces={",".join([iface.ifname for iface in self.interfaces])}'

        linkstr = f'link={self.link and self.link.name}'

        config = self.user_configured and 'yes' or 'no'

        return f'<Gateway name={self.name} {ifstr} available={self.available} {linkstr} config={config}>'

    __repr__ = __str__

    @classmethod
    def _load_gateways(cls):
        if cls._loaded:
            return

        # scan and register all user configured gateway
        for name, config in env.gwconfig.gateways.items():
            cls._gateways[name] = cls(name, config)

        # scan all interfaces, if user does not configure a gateway with same name, register one
        for interface in Interface._interfaces.values():
            if interface.ifname not in cls._gateways:
                cls._gateways[interface.ifname] = cls(interface.ifname, None)

        cls._loaded = True

    @classmethod
    def get(cls, name):
        if not cls._loaded:
            raise Exception('Gateways not loaded, please load gateways before using get()')
        return cls._gateways.get(name)


class NetZone:
    def __init__(self, name, file):
        self.name = name
        self.file = file
        logger.debug(f'Loaded NetZone: {self}')

        with file.open(encoding='utf8') as fp:
            cidr_list = [re.split(';|#| ', line)[0].strip() for line in fp.readlines()]
            cidr_list = [n for n in cidr_list if n]

        self.cidr_list = cidr_list

    # ---- 8< ----

    _netzones = {}
    _loaded = False

    def __str__(self):
        return f'<NetZone name={self.name} cidrs={len(self.cidr_list)} file={self.file}>'

    __repr__ = __str__

    @classmethod
    def _load_netzones(cls):
        if cls._loaded:
            return

        # 扫描所有 netzones 目录并加载
        for path in env.gwconfig.netzone_search_path:
            if not path.exists():
                logger.warning(f'netzone search path does not exist: {path}')
                continue
            for file in path.iterdir():
                if not file.name.endswith('.txt'):
                    continue
                zonename = file.name[:-4]
                if zonename not in cls._netzones:
                    cls._netzones[zonename] = cls(zonename, file)

        cls._loaded = True

    @classmethod
    def get(cls, name):
        if not cls._loaded:
            raise Exception('NetZone not loaded, please load netzones before using get()')
        return cls._netzones.get(name)


def load():
    Interface._load_interfaces()
    Gateway._load_gateways()
    NetZone._load_netzones()
