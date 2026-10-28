"""FinalsPing network engine."""
import collections
import ctypes
import json
import os
import socket
import struct
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import psutil

QREQ = b'QLKN\x00\x00\x00\x09'
QRESP = b'QLKN\x00\x01\x00\x19'
HS_BOOTSTRAP = bytes.fromhex('b401028080ae8d833f000000000000000000000000000000000000000000000000000000000000768d1128d3bfa6489d8d01')

def debug(*args, **kwargs):
    return None

def get_ips():
    return {a.address for li in psutil.net_if_addrs().values() for a in li
            if a.family == socket.AF_INET and not a.address.startswith(('127.', '169.254.'))}

def game_ports():
    pids = {p.info['pid'] for p in psutil.process_iter(['pid', 'name'])
            if (p.info.get('name') or '').lower() == 'discovery.exe'}
    if not pids:
        return False, set()
    return True, {x.laddr.port for x in psutil.net_connections(kind='udp') if x.pid in pids and x.laddr}

def parse_ip_udp(pkt):
    if len(pkt) < 28 or pkt[0] >> 4 != 4 or pkt[9] != 17:
        return None
    h = (pkt[0] & 15) * 4
    if h < 20 or len(pkt) < h + 8 or int.from_bytes(pkt[6:8], 'big') & 0x1fff:
        return None
    sp, dp, length = struct.unpack_from('!HHH', pkt, h)
    if length < 8 or h + length > len(pkt):
        return None
    return socket.inet_ntoa(pkt[12:16]), sp, socket.inet_ntoa(pkt[16:20]), dp, pkt[h+8:h+length]

def hs_match(req, resp):
    return (len(req) >= 10 and len(resp) >= 10 and req[1:3] == b'\x01\x02'
            and resp[:2] == req[:2] and resp[2] == (req[2] ^ 0x80) and resp[3:10] == req[3:10])

def qprobe(ip, port=7600, timeout=1.0):
    token = os.urandom(4)
    payload = QREQ + token + os.urandom(5)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(timeout)
            start = time.perf_counter_ns()
            s.sendto(payload, (ip, port))
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                s.settimeout(max(.001, deadline - time.monotonic()))
                data, src = s.recvfrom(256)
                if src == (ip, port) and len(data) == 33 and data[:8] == QRESP and data[8:12] == token:
                    return round((time.perf_counter_ns() - start) / 1e6, 2)
    except (OSError, socket.timeout):
        pass
    return None

def hsprobe(ip, port, req, timeout=1.5):
    if not req:
        return None
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(timeout)
            s.connect((ip, port))
            start = time.perf_counter_ns()
            s.send(req)
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                s.settimeout(max(.001, deadline - time.monotonic()))
                resp = s.recv(1024)
                if hs_match(req, resp):
                    return round((time.perf_counter_ns() - start) / 1e6, 2)
    except (OSError, socket.timeout):
        return None
    return None

def locate(ip):
    try:
        r = urllib.request.Request('https://ipwho.is/' + ip, headers={'User-Agent': 'FinalsPing/1.0'})
        with urllib.request.urlopen(r, timeout=3) as x:
            data = json.load(x)
        if data.get('success'):
            return {'EU':'EU', 'AS':'Asia', 'NA':'NA', 'SA':'SA', 'OC':'OCE', 'AF':'AF'}.get(
                (data.get('continent_code') or '').upper(), '??'), data.get('city') or ''
    except Exception as e:
        pass
    return '??', ''


SEED_QLKN = [('35.187.53.168', 67.248), ('34.7.158.19', 72.422), ('35.195.201.202', 74.451), ('34.90.7.217', 79.454), ('207.175.184.230', 80.437), ('34.116.158.252', 80.85), ('34.12.11.117', 83.91), ('130.211.74.248', 84.886), ('34.116.228.29', 87.309), ('34.141.240.87', 89.509), ('34.158.231.118', 92.674), ('34.158.238.255', 99.18), ('35.228.234.40', 101.613), ('35.228.214.3', 107.016), ('35.228.93.90', 113.498), ('34.88.73.193', 118.936), ('34.166.215.101', 134.846), ('8.228.200.135', 140.095), ('35.245.69.218', 142.819), ('34.166.112.32', 148.074), ('34.86.91.26', 150.947), ('34.75.165.233', 153.564), ('136.90.72.79', 156.617), ('136.108.203.135', 159.103), ('34.11.27.177', 161.224), ('136.119.12.240', 164.554), ('34.148.210.90', 165.07), ('35.222.162.219', 170.853), ('136.108.149.181', 172.067), ('34.174.25.115', 175.11), ('35.184.127.57', 176.35), ('34.174.101.234', 182.069), ('34.58.91.66', 183.409), ('35.200.221.44', 187.655), ('34.174.222.10', 188.857), ('34.174.6.29', 192.678), ('34.187.185.209', 199.663), ('34.14.128.137', 202.399), ('136.67.185.152', 206.617), ('35.200.215.209', 207.128), ('34.102.104.251', 208.792), ('34.20.173.35', 212.161), ('8.235.122.199', 212.464), ('34.187.148.126', 217.902), ('34.20.174.39', 218.141), ('35.235.71.162', 222.125), ('34.21.224.160', 224.112), ('34.21.250.182', 231.54), ('34.124.211.234', 235.864), ('34.95.223.99', 254.539), ('34.92.149.219', 254.768), ('34.176.254.88', 255.371), ('35.234.51.145', 257.784), ('34.95.192.62', 260.885), ('34.150.127.5', 261.355), ('34.176.165.138', 261.943), ('35.189.191.88', 262.239), ('34.39.229.44', 266.987), ('34.150.86.186', 267.319), ('35.221.254.47', 268.478), ('34.176.232.88', 268.962), ('34.92.121.254', 270.529), ('35.247.205.196', 272.647), ('35.201.240.220', 277.612), ('34.104.221.236', 291.643), ('34.180.86.158', 295.745), ('34.85.8.58', 302.014), ('34.151.101.120', 368.538), ('34.87.244.225', 374.239), ('34.129.78.179', 377.651), ('35.189.48.163', 380.333), ('34.129.206.175', 386.568), ('34.129.72.79', 392.165), ('34.129.180.233', 399.693)]

class State:
    def __init__(self):
        self.lock = threading.RLock()
        self.running = False
        self.ports = set()
        self.ips = get_ips()
        self.flow = collections.defaultdict(lambda: [collections.deque(), collections.deque()])
        self.pending = collections.defaultdict(lambda: collections.deque(maxlen=6))
        self.template = {}
        self.qlkn = {}
        self.match = None
        self.last_packet = 0
        self.error = ''
        self.out_count = 0
        self.in_count = 0
        self.qlkn_count = 0
        self.hs_candidates = 0
        self.hs_raw_out = collections.defaultdict(lambda: collections.deque(maxlen=12))
        self.hs_early_matched = 0
        self.last_prehs = None

    def reset_match(self, match):
        if match != self.match:
            debug('[MATCH]', 'disconnected' if match is None else f'{match[1]}:{match[2]} local={match[0]}', flush=True)
            self.match = match

    def see(self, src, sport, dst, dport, payload, t):
        with self.lock:
            # Capture handshake candidates before UDP process-port discovery catches up.
            # This is crucial when the game opens an ephemeral port immediately before handshake.
            if 7000 <= dport <= 7999 and dport != 7600 and src in self.ips and dst not in self.ips:
                if len(payload) >= 10 and payload[1:3] == b'\x01\x02':
                    self.hs_raw_out[(sport, dst, dport)].append((t, payload))
                    self.hs_candidates += 1
                    self.last_prehs = (sport, dst, dport, len(payload))
                    debug(f'[EARLY HS OUT] {dst}:{dport} local={sport} bytes={len(payload)}', flush=True)
            if 7000 <= sport <= 7999 and sport != 7600 and dst in self.ips and src not in self.ips:
                early_key = (dport, src, sport)
                if early_key not in self.template:
                    for sent, req in reversed(self.hs_raw_out.get(early_key, ())):
                        if 0 < t - sent < 1.5 and hs_match(req, payload):
                            self.template[early_key] = req
                            self.hs_early_matched += 1
                            debug(f'[EARLY HS MATCHED] {src}:{sport} local={dport} RTT={(t-sent)*1000:.1f}ms', flush=True)
                            break
            # Store QLKN replies even when the process UDP port table changes mid-match.
            if sport == 7600 and dst in self.ips and src not in self.ips and len(payload) == 33 and payload[:8] == QRESP:
                # Cache only matchmaking endpoints; the chosen probe doesn't need to repopulate this.
                if self.match is None:
                    self.qlkn[src] = t
                    self.qlkn_count += 1
                    if len(self.qlkn) > 160:
                        for old_ip, _ in sorted(self.qlkn.items(), key=lambda x: x[1])[:len(self.qlkn)-160]:
                            del self.qlkn[old_ip]
            is_out = sport in self.ports and dst not in self.ips
            is_in = dport in self.ports and src not in self.ips
            if not (is_out or is_in):
                return
            if is_out: self.out_count += 1
            else: self.in_count += 1
            remote = dst if is_out else src
            rp = dport if is_out else sport
            local = sport if is_out else dport
            if rp == 7600:
                return
            if not 7000 <= rp <= 7999:
                return
            key = (local, remote, rp)
            if is_out and len(payload) >= 10 and payload[1:3] == b'\x01\x02':
                self.pending[key].append((t, payload))
            if is_in and key not in self.template:
                for sent, req in list(self.pending.get(key, ())):
                    if t - sent < 1.5 and hs_match(req, payload):
                        self.template[key] = req
                        debug(f'[HS TEMPLATE] captured for {remote}:{rp}', flush=True)
                        break
            q = self.flow[key]
            q[0 if is_out else 1].append(t)
            for queue in q:
                while queue and t - queue[0] > 4:
                    queue.popleft()
            if len(q[0]) >= 12 and len(q[1]) >= 12 and len(q[0]) + len(q[1]) >= 65:
                if self.match == key or self.match is None or t - self.last_packet > 2:
                    self.reset_match(key)
                    self.last_packet = t
            elif self.match == key:
                self.last_packet = t
            if len(self.hs_raw_out) > 120:
                for k, qhs in list(self.hs_raw_out.items()):
                    while qhs and t - qhs[0][0] > 20:
                        qhs.popleft()
                    if not qhs:
                        self.hs_raw_out.pop(k, None)
            # Expire stale flows even with little traffic, and bound memory.
            if len(self.flow) > 90:
                for k, v in list(self.flow.items()):
                    if not v[0] and not v[1]:
                        del self.flow[k]

    def get_match(self):
        with self.lock:
            if self.match and time.monotonic() - self.last_packet > 3:
                self.reset_match(None)
                self.flow.clear()
                self.pending.clear()
                self.template.clear()
                self.hs_raw_out.clear()
                self.qlkn.clear()
            return self.match if self.running else None

def process_loop(st, stop):
    while not stop.is_set():
        try:
            running, ports = game_ports()
            with st.lock:
                st.running, st.ports = running, ports
                if not running:
                    st.reset_match(None)
                    st.flow.clear()
                    st.pending.clear()
                    st.template.clear()
                    st.hs_raw_out.clear()
        except Exception as e:
            debug('[PROCESS ERROR]', repr(e), flush=True)
        stop.wait(.45)

def sniff_loop(st, ip, stop):
    raw = None
    try:
        raw = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
        raw.bind((ip, 0))
        raw.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
        raw.settimeout(.4)
        debug('[CAPTURE] started', ip, flush=True)
        while not stop.is_set():
            try:
                pkt = raw.recv(65535)
            except socket.timeout:
                continue
            event = parse_ip_udp(pkt)
            if event:
                st.see(*event, time.monotonic())
    except Exception as e:
        debug('[CAPTURE ERROR]', ip, repr(e), flush=True)
    finally:
        if raw:
            try: raw.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
            except OSError: pass
            raw.close()

def measurement_loop(st, stop, publish):
    active = None
    chosen = None
    last_value = None
    while not stop.is_set():
        match = st.get_match()
        if not match:
            active = None
            chosen = None
            last_value = None
            publish(None)
            stop.wait(.25)
            continue

        local, ip, port = match
        if match != active:
            active = match
            chosen = None
            last_value = None
            publish({'value': None, 'region': '', 'city': '', 'server': f'{ip}:{port}'})
            region, city = locate(ip)
            if stop.is_set() or st.get_match() != match:
                continue
            direct = qprobe(ip, timeout=.7)
            if direct is not None:
                chosen = ip
                last_value = direct
            else:
                with st.lock:
                    req = st.template.get(match) or HS_BOOTSTRAP
                    now = time.monotonic()
                    observed = sorted(((host, ts) for host, ts in st.qlkn.items() if now-ts < 120), key=lambda v: v[1], reverse=True)
                hs = hsprobe(ip, port, req)
                if hs is not None and not stop.is_set() and st.get_match() == match:
                    target = hs - 30
                    hosts = [host for host, _ in observed[:110]]
                    if not hosts:
                        hosts = [host for host, old_ms in sorted(SEED_QLKN, key=lambda x: abs(x[1] - target))[:18]]
                    if hosts:
                        with ThreadPoolExecutor(max_workers=4) as pool:
                            results = list(pool.map(qprobe, hosts))
                        valid = sorted((abs(rtt-target), host, rtt) for host, rtt in zip(hosts, results) if rtt is not None)
                        if valid:
                            _, chosen, last_value = valid[0]
            if stop.is_set() or st.get_match() != match:
                continue
            publish({'value': last_value, 'region': region, 'city': city, 'server': f'{ip}:{port}'})
        if chosen:
            value = qprobe(chosen, timeout=1.0)
            if stop.is_set() or st.get_match() != match:
                continue
            publish({'value': value if value is not None else 999.0, 'region': region, 'city': city, 'server': f'{ip}:{port}'})
        stop.wait(.6)
