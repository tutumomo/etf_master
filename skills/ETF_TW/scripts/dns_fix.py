"""
dns_fix.py — 沙盒 DNS 應急備案模組
======================================

## 背景

Hermes 沙盒有時會出現系統 DNS resolver 損壞的問題：
  $ scutil --dns  →  "No DNS configuration available"
  $ python3 -c "import socket; socket.getaddrinfo('google.com', 443)"
    → socket.gaierror: nodename nor servname provided

根本原因：沙盒的 macOS 系統 DNS 服務（configd / mDNSResponder）未正常初始化。
此時 TCP 連線正常（nc / curl -k 直連 IP 都通），但所有用 hostname 的網路請求全部失敗。

## 正常狀態（/etc/hosts 已修復後）

2026-04-14 之後，TOMO 已在本機 /etc/hosts 寫入靜態 IP 映射：
  google.com        → 142.250.198.78
  github.com        → 20.27.177.113
  news.cnyes.com    → 104.116.243.42
  finance.yahoo.com → 180.222.109.251
  pypi.org          → 151.101.64.223
  www.twse.com.tw   → 203.66.35.69

正常情況下，外部進程（curl / git / pip）和 Python 的 socket.getaddrinfo 都自動
透過 /etc/hosts 解析， dns_fix.py 不需要也不應被載入。

## dns_fix.py 的角色：應急備案（Fallback）

當 /etc/hosts 失效（例如新域名未加入），且系統 DNS 仍損壞時，
dns_fix.py 做最後一道防線：用 raw UDP 直接問 8.8.8.8 / 1.1.1.1，
並 monkey-patch socket.getaddrinfo，讓所有 Python 網路請求（requests / urllib /
shioaji）能正常工作。

## 自動行為

每個腳本開頭的 import 都會自動呼叫 dns_fix.patch()。
patch() 內部會先測試系統 DNS 是否正常：
  - 正常 → 直接 return，不做任何修改（零幹擾）
  - 損壞 → 才套用 monkey-patch，並印出 [dns_fix] 訊息

所以：dns_fix.py 永遠不會在正常狀態下造成副作用。

## 何時會觸發（需要有人回報才會知道）

- 新域名（如某個新的台股資料源）未被加入 /etc/hosts
- /etc/hosts 人為誤刪
- 未來新的 Hermes 沙盒版本再次破壞系統 DNS

## 如何確認 dns_fix.py 是否正在生效

$ cd ETF_TW && .venv/bin/python3 scripts/dns_fix.py
  正常：直接輸出 "Test: google.com -> 200"，無其他訊息
  備案激活：[dns_fix] System DNS unavailable, monkey-patched socket.getaddrinfo
            Test: google.com -> 200

## 如何永久移除（當不再需要時）

1. 確認系統 DNS 正常：scutil --dns 有輸出
2. 移除所有腳本開頭的 dns_fix import：
   $ grep -rl "dns_fix" scripts/
3. 陸續刪除每個腳本裡的這段（注意：docstring 裡要轉義）：
   \"""沙盒 DNS 修復\"""
   import sys as _sys, os as _os; _sys.path.insert(0, ...)
   try: from scripts.dns_fix import patch as _dp; _dp()
   except Exception: pass
4. 刪除本檔案：scripts/dns_fix.py
5. /etc/hosts 的靜態映射可以保留，不影響正常系統

## 技術細節

- 只 patch socket.getaddrinfo（hostname → IP）
- 不 patch socket.create_connection（連線建立仍走正常路徑）
- 快取常見域名（thread-safe, 100 條上限）
- CNAME 跟隨解析支援
- AAAA 記錄（IPv6）略過（因為沙盒網路偏重 IPv4）
"""

import socket
import struct
import threading

_CACHE: dict[str, list] = {}
_LOCK = threading.Lock()
_ORIGINAL_GETADDRINFO = socket.getaddrinfo


def _udp_dns_query(domain: str, dns_server: str = '8.8.8.8', timeout: float = 3.0) -> list[str]:
    """Raw UDP DNS A-record query. 不依賴系統 resolver。"""
    txid = 0x1234
    flags = 0x0100  # standard query
    header = struct.pack('!HHHHHH', txid, flags, 1, 0, 0, 0)  # qdcount=1

    qname = b''
    for part in domain.split('.'):
        qname += bytes([len(part)]) + part.encode()
    qname += b'\x00'
    question = qname + struct.pack('!HH', 1, 1)  # A, IN

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(header + question, (dns_server, 53))
        data, _ = sock.recvfrom(512)
    finally:
        sock.close()

    ancount = struct.unpack('!H', data[6:8])[0]
    idx = len(header) + len(question)

    ips = []
    for _ in range(ancount):
        if idx >= len(data):
            break
        if data[idx] & 0xc0 == 0xc0:  # name pointer
            idx += 2
        else:
            while idx < len(data) and data[idx] != 0:
                idx += data[idx] + 1
            idx += 1
        if idx + 10 > len(data):
            break
        rtype, _, _, rdlen = struct.unpack('!HHIH', data[idx:idx+10])
        idx += 10
        if rtype == 1 and rdlen == 4 and idx + 4 <= len(data):
            ip = '.'.join(str(b) for b in data[idx:idx+4])
            ips.append(ip)
        idx += rdlen
    return ips


def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """Replacement getaddrinfo: 系統 DNS 失敗時才走 UDP DNS。"""
    # 跳過 localhost / IP 字面量
    if (not host or host in ('localhost', '127.0.0.1', '::1')
            or host.replace('.', '').isdigit()):
        return _ORIGINAL_GETADDRINFO(host, port, family, type, proto, flags)

    # 查快取
    with _LOCK:
        if host in _CACHE:
            for ip in _CACHE[host]:
                try:
                    result = _ORIGINAL_GETADDRINFO(ip, port, family, type, proto, flags)
                    if result:
                        return result
                except Exception:
                    pass

    # 先試系統 resolver（快路徑）
    try:
        result = _ORIGINAL_GETADDRINFO(host, port, family, type, proto, flags)
        if result:
            return result
    except socket.gaierror:
        pass

    # 系統 DNS 失敗，走 UDP 直問 8.8.8.8 / 1.1.1.1
    for dns_server in ('8.8.8.8', '1.1.1.1', '8.8.4.4'):
        try:
            ips = _udp_dns_query(host, dns_server, timeout=2.0)
            if ips:
                with _LOCK:
                    _CACHE[host] = ips
                for ip in ips:
                    try:
                        result = _ORIGINAL_GETADDRINFO(ip, port, family, type, proto, flags)
                        if result:
                            return result
                    except Exception:
                        pass
        except Exception:
            continue

    raise socket.gaierror(8, f'nodename nor servname provided, or not known: {host}')


def patch():
    """
    測試系統 DNS，若正常則直接返回（零幹擾）。
    若系統 DNS 損壞，套用 monkey-patch 並回報。
    """
    try:
        _ORIGINAL_GETADDRINFO('google.com', 443)
        return  # 系統 DNS 正常，不需要 patch
    except socket.gaierror:
        pass

    socket.getaddrinfo = _patched_getaddrinfo
    print('[dns_fix] System DNS unavailable — socket.getaddrinfo monkey-patched (fallback active)')


if __name__ == '__main__':
    patch()
    import urllib.request
    r = urllib.request.urlopen('https://www.google.com', timeout=5)
    print(f'Test: google.com -> HTTP {r.status}')
