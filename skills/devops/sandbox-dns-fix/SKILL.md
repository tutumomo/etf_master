---
name: sandbox-dns-fix
description: Fix Hermes sandbox DNS failure — monkey-patch socket.getaddrinfo with direct UDP DNS queries to 8.8.8.8. Also covers /etc/hosts fallback for non-Python processes (git/pip/curl).
tags: [dns, sandbox, hermes, macos, monkey-patch, networking]
---

# Sandbox DNS Fix

**Problem**: Hermes sandbox on macOS sometimes has broken system DNS resolver.
- `scutil --dns` → "No DNS configuration available"
- All hostname-based connections fail (Python, curl, git)
- But TCP connections to IPs work fine (netcat, curl --resolve)

**Root cause**: Sandbox process doesn't inherit macOS DNS configuration from configd/mDNSResponder.

## Diagnosis

```bash
# 1. Check if DNS is broken
scutil --dns
# "No DNS configuration available" = broken

# 2. Confirm TCP works (just DNS is broken)
nc -z -w 3 142.250.196.206 443 && echo "TCP OK" || echo "TCP FAIL"
curl -s -o /dev/null -w '%{http_code}' --resolve google.com:443:142.250.196.206 https://google.com
# Returns 200 = TCP fine, DNS broken
```

## Fix A: Python (dns_fix.py monkey-patch)

For all Python network code (requests, urllib, shioaji):

```python
# Add at top of any script that does network calls:
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
try: from scripts.dns_fix import patch as _dp; _dp()
except Exception: pass
```

The dns_fix.py module:
1. Tests if system resolver works (fast path)
2. If broken: does raw UDP DNS A-record queries to 8.8.8.8 / 1.1.1.1 / 8.8.4.4
3. Caches results in a dict
4. Monkey-patches `socket.getaddrinfo` to use UDP results when system resolver fails
5. Falls back gracefully to original error if all DNS servers fail

**Critical pitfall**: Do NOT set `urllib3.util.connection.create_connection = None` — this destroys requests' ability to create connections entirely.

## Fix B: Non-Python processes (git/pip/curl)

These use system `getaddrinfo()` and don't inherit Python's monkey-patch. Options:

### Option 1: /etc/hosts (requires sudo)
```bash
echo '20.27.177.113 github.com
140.82.121.5 codeload.github.com
185.199.108.133 raw.githubusercontent.com' | sudo tee -a /etc/hosts
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder
```

## /etc/hosts Essential Domain List (macOS Sandbox)

When DNS is broken, these domains must be in /etc/hosts for various ETF_TW tools to work:

```bash
# Yahoo Finance (used by sync_ohlcv_history.py via curl/yfinance)
180.222.109.251 query1.finance.yahoo.com
180.222.109.252 query2.finance.yahoo.com
180.222.109.251 edge.gycpi.b.yahoodns.net

# Google
142.250.198.78 google.com
142.251.157.119 www.google.com

# GitHub
20.27.177.113 github.com
20.27.177.116 api.github.com
20.27.177.114 codeload.github.com
185.199.111.133 raw.githubusercontent.com
20.27.177.113 gist.github.com
151.101.193.194 github.global.ssl.fastly.net

# Taiwan finance
104.116.243.42 news.cnyes.com
104.116.243.42 www.cnyes.com
203.66.35.69 www.twse.com.tw

# PyPI
151.101.64.223 pypi.org
151.101.192.223 files.pythonhosted.org
```

To find the correct IPs, use `host domain.com` or `getent hosts domain.com` (both bypass the broken system resolver and query DNS directly).

### Option 2: networksetup (requires sudo)
```bash
sudo networksetup -setdnsservers "Wi-Fi" 8.8.8.8 1.1.1.1
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder
```

### Option 3: Environment variable (pip only)
```bash
PIP_INDEX_URL=http://pypi.python.org/simple pip install <package>
```

## Embedding dns_fix in ETF_TW Scripts

Already patched into these scripts (add 4 lines after shebang):
- `sync_etf_universe_tw.py`
- `sync_news_from_local.py`
- `generate_llm_event_context.py`
- `generate_llm_decision_reasoning.py`
- `etf_core/utils/news_crawler.py`
- `run_auto_decision_scan.py`

The 4-line boilerplate:
```python
\"""沙盒 DNS 修復\"""
import sys as _sys, os as _os; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
try: from scripts.dns_fix import patch as _dp; _dp()
except Exception: pass
```

**⚠️ Critical**: Use `\"""` not `"""` in the inline docstring. The docstring uses Chinese characters — if the first `"""` is unescaped, Python treats it as the module-level docstring terminator, causing `SyntaxError: invalid syntax` at `import socket` (which Python thinks is inside a string). This is because the module-level docstring starts at line 1 with `"""`, and the second `"""` at line 2 of the boilerplate prematurely closes it.

Also: if the script uses `from __future__ import annotations`, that MUST come immediately after the shebang line — before any other import including the dns_fix hook.

For scripts in subdirectories (e.g., `etf_core/utils/`), change `'..'` to `'../..''`.