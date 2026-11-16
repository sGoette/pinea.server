import asyncio
import ipaddress
import os
import re
import socket
import unicodedata
from zeroconf import NonUniqueNameException, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

import logging
log = logging.getLogger(__name__)

SERVICE_TYPE = "_pinea._tcp.local."
SERVICE_PORT = 4000
ADVERTISE_IP_ENV = "PINEA_ADVERTISE_IP"  # optional override, e.g. in a systemd drop-in
WAIT_FOR_NETWORK_SECONDS = 60


def _is_usable(ip: str) -> bool:
    """Loopback (127.x) and self-assigned link-local addresses (169.254.x) are useless for clients."""
    try:
        address = ipaddress.IPv4Address(ip)
    except ValueError:
        return False
    return not (address.is_loopback or address.is_link_local or address.is_unspecified)


def _default_route_ip() -> str | None:
    """Address of the interface that has the default route, i.e. the main LAN interface.
    Other interfaces (internal storage networks, container bridges) are ignored."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Nothing is sent. connect() on UDP only selects the outgoing interface.
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return None  # no default route (yet)
    finally:
        s.close()


async def get_advertise_ip() -> str:
    """The IPv4 address announced via Bonjour. Waits for the network if it isn't up yet."""
    override = os.environ.get(ADVERTISE_IP_ENV)
    if override:
        if not _is_usable(override):
            raise RuntimeError(f"{ADVERTISE_IP_ENV}={override} is not a usable IPv4 address")
        return override

    for attempt in range(WAIT_FOR_NETWORK_SECONDS):
        ip = _default_route_ip()
        if ip and _is_usable(ip):
            return ip
        if attempt == 0:
            log.warning(f"[Bonjour] No usable LAN address yet (got {ip}), waiting for the network…")
        await asyncio.sleep(1)

    raise RuntimeError(f"No usable LAN IPv4 address found for Bonjour. Is the network up? You can set {ADVERTISE_IP_ENV}.")


def mdns_hostname(server_name: str) -> str:
    """A valid mDNS host name from the server name: "The Pinea Server" -> "the-pinea-server.local.".
    Host names may only contain letters, digits and hyphens (no underscores, spaces or umlauts)."""
    ascii_name = unicodedata.normalize("NFKD", server_name).encode("ascii", "ignore").decode()
    label = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:63].strip("-")
    return f"{label or 'pinea-server'}.local."


def build_service_info(server_name: str, host_ip: str) -> ServiceInfo:
    return ServiceInfo(
        type_=SERVICE_TYPE,
        name=f"{server_name}.{SERVICE_TYPE}",   # shown in the tvOS app
        addresses=[socket.inet_aton(host_ip)],
        port=SERVICE_PORT,
        properties={
            b"api": b"/api",   # base path for API
            b"version": b"1",
        },
        server=mdns_hostname(server_name),
    )


# --- Live rename (server name changed in the settings) ---

MAX_NAME_BYTES = 63  # DNS label limit for the service instance name

class NameInUseError(Exception):
    pass

_rename_lock = asyncio.Lock()


def service_display_name(info: ServiceInfo) -> str:
    """'The Pinea Server._pinea._tcp.local.' -> 'The Pinea Server'"""
    return info.name.removesuffix(f".{SERVICE_TYPE}")


async def rename_service(zeroconf: AsyncZeroconf, current: ServiceInfo, new_name: str) -> ServiceInfo:
    """Re-announce the service under a new name, without a restart.
    Raises NameInUseError (and keeps the old announcement) if another service already uses the name."""
    async with _rename_lock:
        new_info = build_service_info(new_name, current.parsed_addresses()[0])
        await (await zeroconf.async_unregister_service(current))
        try:
            await (await zeroconf.async_register_service(new_info))
        except NonUniqueNameException:
            await (await zeroconf.async_register_service(current))
            raise NameInUseError(new_name)
        log.info(f"[Bonjour] Renamed '{service_display_name(current)}' -> '{new_name}' ({new_info.server})")
        return new_info
