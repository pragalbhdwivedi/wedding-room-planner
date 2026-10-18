"""Transport checks shared with the dependency-free host provisioner."""
from ipaddress import ip_address, ip_network
from urllib.parse import urlparse

PRIVATE_NETWORKS = tuple(ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))


def private_address(value: str) -> bool:
    try:
        address = ip_address(value)
        return address.is_loopback or (address.version == 4 and any(address in network for network in PRIVATE_NETWORKS))
    except ValueError:
        return False


def lan_origin(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return (parsed.scheme in {"http", "https"} and parsed.hostname is not None
                and (parsed.hostname == "localhost" or private_address(parsed.hostname))
                and parsed.username is None and parsed.password is None
                and parsed.path in {"", "/"} and not parsed.query and not parsed.fragment
                and (parsed.port is None or 1 <= parsed.port <= 65535))
    except ValueError:
        return False
