"""Deterministic NON-credential matching GitLab 19.4.2 RoutableToken syntax.

Models the installed public encoder; never uses a live runner or secret entropy.
The CRC is format metadata, not credential authentication or a signature.
"""
import base64,zlib

def base36(value):
    result=''
    while value:
        value,digit=divmod(value,36);result='0123456789abcdefghijklmnopqrstuvwxyz'[digit]+result
    return result or '0'

def routable_runner_token():
    payload=b'o:1\np:v\nt:3\nu:l'  # synthetic routing IDs: project 31, actor 21
    encoded=base64.urlsafe_b64encode(bytes(range(16))+payload+bytes([len(payload)])).decode().rstrip('=')
    prefixed='glrt-'+encoded+'.01.'+base36(len(encoded)).rjust(2,'0')
    return prefixed+base36(zlib.crc32(prefixed.encode())).rjust(7,'0')
