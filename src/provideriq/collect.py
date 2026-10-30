"""Polite collection of public web pages: robots.txt respected, rate-limited, identified."""
import hashlib, json, os, re, time
import urllib.robotparser as robotparser
from urllib.parse import urlparse
import requests

CONTACT = os.getenv("SCRAPER_CONTACT", "your-email@example.com")
UA = f"ProviderIQ-research/1.0 (+{CONTACT})"


def robots_allows(url):
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    rp = robotparser.RobotFileParser()
    try:
        r = requests.get(base + "/robots.txt", headers={"User-Agent": UA}, timeout=15)
        if r.status_code == 404:
            return True  # no robots.txt = no restrictions stated
        r.raise_for_status()
        rp.parse(r.text.splitlines())
        return rp.can_fetch(UA, url)
    except requests.RequestException:
        return False  # be conservative if robots.txt cannot be read


def slug(url):
    host = re.sub(r"\W+", "_", urlparse(url).netloc)
    return f"{host}_{hashlib.md5(url.encode()).hexdigest()[:8]}"


def collect(seed_file="seeds.txt", out_dir="data/raw", delay=2.0):
    os.makedirs(out_dir, exist_ok=True)
    log = []
    urls = [l.strip() for l in open(seed_file) if l.strip() and not l.startswith("#")]
    for url in urls:
        entry = {"url": url}
        if not robots_allows(url):
            entry["result"] = "skipped: robots.txt disallows (or unreadable)"
        else:
            try:
                r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
                r.raise_for_status()
                path = os.path.join(out_dir, slug(url) + ".html")
                open(path, "w", encoding="utf-8").write(f"<!-- source: {url} -->\n" + r.text)
                entry["result"] = "saved"
            except requests.RequestException as e:
                entry["result"] = f"error: {e.__class__.__name__}"
            time.sleep(delay)
        log.append(entry)
        print(entry["result"], url)
    json.dump(log, open(os.path.join(out_dir, "_collect_log.json"), "w"), indent=2)
    return log


if __name__ == "__main__":
    collect()
