#!/usr/bin/python3
"""Synthetic packet verification only. No configuration or lifecycle mutations.

Run ONLY through packet-fixture.yml in pfpxe-s/pfpxe-c. Standard library only.
PXE vendor boot item: dnsmasq v2.91 rfc2131.c, suboption71/type32768/layer0.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import struct
import subprocess
import time

SERVER = '192.0.2.10'
PILOT = '192.0.2.11'
OTHER = '192.0.2.12'
MAC = bytes.fromhex('020000000011')
UNKNOWN = bytes.fromhex('020000000099')
SERVER_MAC = bytes.fromhex('020000000010')
CONTENT = b'PXE fixture: public dummy data\n'
BOOTFILE = b'EFI/BOOT/BOOTX64.EFI'


def options(data):
    result = {}
    i = 0
    while i < len(data):
        code = data[i]
        i += 1
        if code == 255:
            break
        if code == 0:
            continue
        if i >= len(data) or i + 1 + data[i] > len(data):
            raise ValueError('Truncated DHCP option')
        size = data[i]
        result[code] = data[i + 1:i + 1 + size]
        i += size + 1
    return result


def checksum(data):
    if len(data) % 2:
        data += b'\0'
    total = sum(struct.unpack('!%dH' % (len(data) // 2), data))
    while total >> 16:
        total = (total & 65535) + (total >> 16)
    return (~total) & 65535


def request(xid, mac=MAC, port=67, arch=7):
    ciaddr = b'\0' * 4 if port == 67 else socket.inet_aton(PILOT)
    header = struct.pack('!BBBBIHH4s4s4s4s16s64s128s', 1, 1, 6, 0, xid,
                         0, 0x8000, ciaddr, b'\0'*4, b'\0'*4, b'\0'*4,
                         mac + b'\0'*10, b'\0'*64, b'\0'*128)
    def opt(code, value):
        return bytes([code, len(value)]) + value
    opts = opt(53, bytes([1 if port == 67 else 3]))
    opts += opt(60, f'PXEClient:Arch:{arch:05}:UNDI:003016'.encode())
    opts += opt(93, struct.pack('!H', arch)) + opt(94, b'\x01\x03\x10')
    opts += opt(97, b'\0' + bytes.fromhex('00112233445566778899aabbccddeeff'))
    opts += opt(55, bytes([43, 54, 60, 66, 67]))
    if port == 4011:
        opts += opt(43, bytes([71, 4]) + struct.pack('!HH', 32768, 0) + b'\xff')
    return header + b'\x63\x82\x53\x63' + opts + b'\xff'


def frame(payload, mac, port, sport=68):
    source = '0.0.0.0' if port == 67 else PILOT
    destination = '255.255.255.255' if port == 67 else SERVER
    udp = struct.pack('!HHHH', sport, port, len(payload) + 8, 0) + payload
    ip = struct.pack('!BBHHHBBH4s4s', 0x45, 0, 20+len(udp), 1, 0, 64, 17, 0,
                     socket.inet_aton(source), socket.inet_aton(destination))
    ip = ip[:10] + struct.pack('!H', checksum(ip)) + ip[12:]
    dest = b'\xff'*6 if port == 67 else SERVER_MAC
    return dest + mac + b'\x08\x00' + ip + udp


def decode(raw):
    if len(raw) < 42 or raw[12:14] != b'\x08\x00' or raw[23] != 17:
        return None
    ihl = (raw[14] & 15)*4
    start = 14 + ihl
    if ihl < 20 or len(raw) < start + 8:
        return None
    sport, dport, length, _ = struct.unpack('!HHHH', raw[start:start+8])
    payload = raw[start+8:start+length]
    if len(payload) < 240 or payload[236:240] != b'\x63\x82\x53\x63':
        return None
    return dict(op=payload[0], xid=struct.unpack('!I', payload[4:8])[0],
                sport=sport, dport=dport, yiaddr=socket.inet_ntoa(payload[16:20]),
                siaddr=socket.inet_ntoa(payload[20:24]),
                mac=payload[28:34].hex(), file=payload[108:236].split(b'\0')[0],
                opts=options(payload[240:]))


def require_namespace(expected):
    actual = subprocess.check_output(['/usr/bin/ip', 'netns', 'identify', str(os.getpid())],
                                     text=True).strip()
    if actual != expected:
        raise RuntimeError(f'Refusing sockets outside expected namespace {expected}')


def observe(path):
    require_namespace('pfpxe-s')
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0800)) as sock:
        sock.bind(('fixture0', 0))
        sock.settimeout(1)
        deadline = time.monotonic() + 150
        # Exclusive creation; no arbitrary overwrite. Root-created fixture parent only.
        with open(path, 'x', encoding='utf-8') as log:
            os.chmod(path, 0o600)
            log.write(json.dumps({'ready': True})+'\n')
            log.flush()
            count = 0
            while time.monotonic() < deadline and count < 512:
                try:
                    packet = decode(sock.recv(65535))
                except socket.timeout:
                    continue
                if packet and packet['op'] == 1 and packet['dport'] in (67, 4011):
                    log.write(json.dumps({k: packet[k] for k in ('xid', 'dport', 'mac')})+'\n')
                    log.flush()
                    count += 1


class Probes:
    def __init__(self):
        self.events = []

    def dhcp(self, port, allowed, mac=MAC, arch=7, boot=True):
        xid = secrets.randbits(32)
        self.events.append(dict(xid=xid, dport=port, mac=mac.hex()))
        received = []
        with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0800)) as sock:
            sock.bind(('client0', 0))
            sock.settimeout(0.15)
            for _ in range(2):
                sock.send(frame(request(xid, mac, port, arch), mac, port))
                deadline = time.monotonic()+1
                while time.monotonic() < deadline:
                    try:
                        reply = decode(sock.recv(65535))
                    except socket.timeout:
                        continue
                    if reply and reply['op'] == 2 and reply['xid'] == xid:
                        received.append(reply)
                if received:
                    break
        if not allowed:
            assert not received, f'Unexpected DHCP/PXE response port={port} mac={mac.hex()}'
            return
        assert received, f'Missing positive DHCP/PXE control port={port}'
        for reply in received:
            assert reply['opts'].get(53) == bytes([2 if port == 67 else 5])
            assert reply['mac'] == mac.hex()
            assert reply['yiaddr'] == ('0.0.0.0' if port == 67 else PILOT), 'Unexpected address allocation'
            assert reply['opts'].get(54) == socket.inet_aton(SERVER)
            if port == 4011:
                assert reply['siaddr'] == SERVER and reply['file'] == BOOTFILE
                assert options(reply['opts'][43])[71] == struct.pack('!HH',32768,0)
            elif boot:
                assert reply['siaddr'] == SERVER, 'Missing proxy boot-server information'
            else:
                assert not reply['file']
                assert 9 not in options(reply['opts'].get(43, b'')), 'Unexpected wrong-architecture menu'

    def http(self, source, expected, name='public-fixture.txt'):
        try:
            with socket.socket() as sock:
                sock.settimeout(2)
                sock.bind((source, 0))
                sock.connect((SERVER, 8080))
                sock.sendall(('GET /rhel-10.2/'+name+' HTTP/1.0\r\nHost: fixture\r\n\r\n').encode())
                data = b''
                while True:
                    block = sock.recv(65535)
                    if not block:
                        break
                    data += block
        except (TimeoutError, ConnectionError):
            assert expected == 'drop', 'Positive HTTP control failed'
            return
        assert expected != 'drop', 'Expected firewall drop but HTTP responded'
        assert data.startswith(b'HTTP/1.1 '+expected.encode()) or data.startswith(b'HTTP/1.0 '+expected.encode())
        if expected == '200':
            assert data.split(b'\r\n\r\n', 1)[1] == CONTENT

    def tftp(self, source, allowed, name='public-fixture.txt'):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(2)
            sock.bind((source, 0))
            sock.sendto(b'\0\x01'+name.encode()+b'\0octet\0', (SERVER, 69))
            try:
                data, peer = sock.recvfrom(65535)
            except socket.timeout:
                assert not allowed, 'Positive TFTP control failed'
                return
            assert allowed, 'Unauthorized source received TFTP data or error'
            assert peer[0] == SERVER
            if name == 'public-fixture.txt':
                assert data[:4] == b'\0\x03\0\x01' and data[4:] == CONTENT
                sock.sendto(b'\0\x04\0\x01', peer)
            else:
                assert data[:4] == b'\0\x05\0\x01', 'Missing file did not produce not-found TFTP error'

    def raw_tftp(self, mac, allowed):
        port = 40000 + secrets.randbelow(10000)
        with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0800)) as sock:
            sock.bind(('client0', 0))
            sock.settimeout(0.1)
            sock.send(frame(b'\0\x01public-fixture.txt\0octet\0', mac, 69, port))
            deadline = time.monotonic()+2
            response = None
            while time.monotonic() < deadline:
                try:
                    raw = sock.recv(65535)
                except socket.timeout:
                    continue
                if len(raw)<42 or raw[12:14]!=b'\x08\x00' or raw[23]!=17:
                    continue
                start=14+(raw[14]&15)*4
                sport,dport,length,_=struct.unpack('!HHHH',raw[start:start+8])
                if dport==port and raw[26:30]==socket.inet_aton(SERVER):
                    response=raw[start+8:start+length]
                    if response[:4]==b'\0\x03\0\x01':
                        sock.send(frame(b'\0\x04\0\x01', MAC, sport, port))
                    break
            if allowed:
                assert response == b'\0\x03\0\x01'+CONTENT, 'Raw TFTP positive failed'
            else:
                assert response is None, 'Wrong-MAC TFTP received a response'

    def suite(self, phase):
        if phase == 'wrong-interface':
            require_namespace('pfpxe-s')
            self.http('127.0.0.1', 'drop')
            self.tftp('127.0.0.1', False)
            print(json.dumps({'phase': phase, 'result': 'PASS', 'requests': []}))
            return
        require_namespace('pfpxe-c')
        if phase == 'control':
            self.dhcp(67, True)
            self.dhcp(4011, True)
            self.http(PILOT, '200')
            self.tftp(PILOT, True)
            print(json.dumps({'phase': phase, 'result': 'PASS', 'requests': self.events}))
            return
        for port in (67, 4011):
            self.dhcp(port, True)
            self.dhcp(port, False, mac=UNKNOWN)
            self.dhcp(port, True)
        self.dhcp(67, True, arch=0, boot=False)
        self.dhcp(67, True)
        if phase == 'guarded':
            self.raw_tftp(MAC, True)
            self.raw_tftp(UNKNOWN, False)
            self.raw_tftp(MAC, True)
        # Architecture0 has no matching service. Some proxy offers may still exist;
        # do not equate an OFFER with executable boot service or assert unsupported
        # architecture is an access-control boundary (4011 boot-item path differs).
        self.http(PILOT, '200')
        self.http(OTHER, '403' if phase == 'daemon' else 'drop')
        self.http(PILOT, '200')
        self.http(PILOT, '404', 'missing-fixture.txt')
        self.tftp(PILOT, True)
        if phase == 'guarded':
            self.tftp(OTHER, False)
            self.tftp(PILOT, True)
        else:
            # Demonstrate why the independent ingress guard is necessary.
            self.tftp(OTHER, True)
        self.tftp(PILOT, True, 'missing-fixture.txt')
        print(json.dumps({'phase': phase, 'result': 'PASS', 'requests': self.events}, sort_keys=True))


def verify_observations(paths):
    assert len(paths) >= 3
    observed = [json.loads(line) for line in Path(paths[0]).read_text().splitlines()]
    seen = {(v['xid'], v['dport'], v['mac']) for v in observed if 'xid' in v}
    expected = set()
    for path in paths[1:]:
        result = json.loads(Path(path).read_text())
        assert result['result'] == 'PASS'
        expected.update((v['xid'], v['dport'], v['mac']) for v in result['requests'])
    assert expected and expected <= seen, 'Server did not observe every emitted DHCP/PXE transaction'
    print(json.dumps({'server_observation': 'PASS', 'transactions': len(expected)}))


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--observe')
    group.add_argument('--phase', choices=('daemon', 'guarded', 'wrong-interface', 'control'))
    group.add_argument('--verify-observations', nargs='+')
    args = parser.parse_args()
    if args.observe:
        observe(args.observe)
    elif args.verify_observations:
        verify_observations(args.verify_observations)
    else:
        Probes().suite(args.phase)


if __name__ == '__main__':
    main()
