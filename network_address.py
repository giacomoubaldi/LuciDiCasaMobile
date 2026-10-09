"""Find the Wi-Fi IPv4 address, including Android's restricted Termux setup."""
import ipaddress
import json
import shutil
import socket
import subprocess


def _usable(value):
    try:
        address = ipaddress.ip_address(value)
        return str(address) if address.version == 4 and not (address.is_loopback or address.is_unspecified or address.is_link_local) else None
    except ValueError:
        return None


def wifi_ip(device_ips=()):
    # Termux:API works even on Android versions that block netlink/ioctl.
    if shutil.which('termux-wifi-connectioninfo'):
        try:
            result = subprocess.run(['termux-wifi-connectioninfo'], capture_output=True, text=True, timeout=3)
            address = _usable(json.loads(result.stdout).get('ip', ''))
            if address:
                return address
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
    try:
        import fcntl
        import struct
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            info = fcntl.ioctl(sock.fileno(), 0x8915, struct.pack('256s', b'wlan0'))
            address = _usable(socket.inet_ntoa(info[20:24]))
            if address:
                return address
    except (ImportError, OSError):
        pass
    # Ask the routing table which local address reaches a configured LAN lamp.
    # UDP connect sends no packet and does not require the lamp to be online.
    for destination in device_ips:
        try:
            target = ipaddress.ip_address(destination)
            if target.version != 4 or not target.is_private or target.is_loopback:
                continue
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect((str(target), 80))
                address = _usable(sock.getsockname()[0])
                if address:
                    return address
        except (ValueError, OSError):
            pass
    return None


def print_addresses(port, device_ips=()):
    print('\nLuci di Casa Mobile', flush=True)
    print(f'Su questo telefono: http://127.0.0.1:{port}', flush=True)
    address = wifi_ip(device_ips)
    if address:
        print(f'Dagli altri dispositivi sullo stesso Wi-Fi: http://{address}:{port}', flush=True)
    else:
        print('IP Wi-Fi non rilevato: leggi l’indirizzo nelle Impostazioni Wi-Fi del telefono.', flush=True)
        print(f'Dagli altri dispositivi: http://IP_DEL_TELEFONO:{port}', flush=True)
    print('Lascia Termux attivo. Per arrestare il server: Ctrl+C.\n', flush=True)
