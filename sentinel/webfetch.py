"""Fetch a web page the way an agent's web tool would, and flatten it to text.

Agent web tools hand the model *everything* in the page text, including things a human never sees: HTML
comments, visually hidden elements, image alt text. Those are exactly where prompt injections hide, so we keep
them (comments are re-emitted as ``<!-- ... -->`` lines).
"""
from __future__ import annotations

import ipaddress
import re
import socket
import urllib.request
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Comment

MAX_BYTES = 1_500_000
MAX_CHARS = 20_000
UA = "Mozilla/5.0 (compatible; SentinelDemo/1.0; +local)"


class FetchError(Exception):
    pass


def _check_url(url: str, allow_private: bool):
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise FetchError("Only http(s) URLs are supported.")
    if allow_private:
        return
    local_demo = u.hostname in ("localhost", "127.0.0.1") and u.path.startswith("/demo/")
    if local_demo:
        return
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80))
    except socket.gaierror:
        raise FetchError("Could not resolve that host.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise FetchError("That address is on a private network; only public pages can be fetched.")


def html_to_text(html: str) -> tuple[str, str]:
    """Return (title, text). Comments, hidden elements and alt text are kept on purpose."""
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        c.replace_with(f"\n<!-- {str(c).strip()} -->\n")
    for t in soup(["script", "style", "noscript", "template", "svg", "iframe"]):
        t.decompose()
    for img in soup.find_all("img"):
        alt = (img.get("alt") or "").strip()
        img.replace_with(f"\n{alt}\n" if len(alt) > 12 else "\n")
    text = soup.get_text("\n")
    lines, seen_blank = [], False
    for raw in text.split("\n"):
        line = re.sub(r"[ \t ]+", " ", raw).strip()
        if not line:
            continue
        lines.append(line)
    return title, "\n".join(lines)


def fetch_text(url: str, timeout: float = 10.0, allow_private: bool = False) -> dict:
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    _check_url(url, allow_private)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,text/plain;q=0.9,*/*;q=0.5"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ctype = r.headers.get("Content-Type", "")
            raw = r.read(MAX_BYTES + 1)
            charset = r.headers.get_content_charset() or "utf-8"
    except Exception as e:  # noqa: BLE001
        raise FetchError(f"Could not fetch that page ({type(e).__name__}: {e}).")
    if len(raw) > MAX_BYTES:
        raw = raw[:MAX_BYTES]
    body = raw.decode(charset, errors="replace")
    if "html" in ctype.lower() or body.lstrip().lower().startswith(("<!doctype", "<html")):
        title, text = html_to_text(body)
    else:
        title, text = "", body
    truncated = len(text) > MAX_CHARS
    return {"url": url, "title": title, "text": text[:MAX_CHARS], "chars": len(text), "truncated": truncated}
