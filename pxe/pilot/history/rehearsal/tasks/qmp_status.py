"""Read-only QMP status of this fixture's private UNIX socket. Never sends mutations."""
import argparse
import json
import re
import socket


def response(stream, identifier):
    for _ in range(32):
        line = stream.readline()
        if not line:
            raise ValueError('QMP closed before expected response')
        value = json.loads(line)
        if value.get('id') == identifier:
            if 'error' in value or 'return' not in value:
                raise ValueError('QMP rejected read-only query')
            return value['return']
    raise ValueError('QMP response bound exceeded')


def query(stream):
    greeting = json.loads(stream.readline())
    if 'QMP' not in greeting:
        raise ValueError('Not a QMP greeting')
    stream.write(b'{"execute":"qmp_capabilities","id":"cap"}\n'); stream.flush()
    response(stream, 'cap')
    stream.write(b'{"execute":"query-status","id":"status"}\n'); stream.flush()
    status = response(stream, 'status')['status']
    if not isinstance(status, str) or not re.fullmatch('[a-z-]+', status):
        raise ValueError('Invalid VM status')
    return status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('socket')
    args = parser.parse_args()
    if not re.fullmatch(r'/var/lib/perkforge-pxe-rehearsal/[a-z0-9][a-z0-9-]{7,23}/vm/qmp\.sock', args.socket):
        parser.error('Only an explicitly named private rehearsal socket is allowed')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(3)
        connection.connect(args.socket)
        with connection.makefile('rwb', buffering=0) as stream:
            print(json.dumps({'status': query(stream)}))

if __name__ == '__main__':
    main()
