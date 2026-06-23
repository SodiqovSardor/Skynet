"""
Skynet DNS Bruteforce — Subdomain enumeration via iterative DNS resolution.
Discovers hidden subdomains using a built-in wordlist.
"""
import socket
import concurrent.futures
import json

SUBDOMAIN_WORDLIST = [
    "www", "mail", "ftp", "admin", "api", "dev", "test", "staging", "blog",
    "webmail", "web", "app", "portal", "ssh", "vpn", "remote", "git", "svn",
    "jenkins", "jira", "confluence", "wiki", "support", "help", "helpdesk",
    "status", "monitor", "monitoring", "dashboard", "panel", "cpanel",
    "whm", "plesk", "direct", "directadmin", "phpmyadmin", "phpadmin",
    "mysql", "database", "db", "sql", "backup", "beta", "alpha", "demo",
    "shop", "store", "billing", "payment", "gateway", "secure", "ssl",
    "cdn", "static", "assets", "img", "images", "css", "js", "download",
    "downloads", "upload", "uploads", "files", "file", "media", "video",
    "videos", "tv", "radio", "stream", "streaming", "live", "chat",
    "community", "forum", "forums", "board", "boards", "news", "newsletter",
    "register", "signup", "sign-up", "login", "log-in", "auth", "oauth",
    "identity", "sso", "saml", "ldap", "radius", "radius-1", "radius1",
    "ns1", "ns2", "ns3", "ns4", "dns1", "dns2", "mx", "pop3", "imap",
    "smtp", "relay", "sip", "voip", "phone", "call", "calls",
    "proxy", "proxies", "squid", "traffic", "cache", "caching",
    "cloud", "aws", "azure", "gcp", "google", "amazon", "microsoft",
    "office", "exchange", "owa", "outlook", "lync", "skype",
    "teams", "slack", "discord", "mattermost", "riot",
    "ci", "cd", "build", "builder", "deploy", "deployment",
    "release", "artifact", "artifacts", "nexus", "artifactory",
    "docker", "k8s", "kubernetes", "swarm", "rancher",
    "prometheus", "grafana", "kibana", "elastic", "logstash",
    "metrics", "influxdb", "timescaledb", "cassandra",
    "redis", "memcached", "rabbitmq", "kafka", "mqtt",
    "sensor", "sensors", "iot", "robot", "robots",
    "lms", "crm", "erp", "hrm", "scm", "wms",
    "redirect", "redir", "go", "click", "link",
    "sites", "site", "pages", "page", "home", "main",
    "info", "about", "contact", "team", "careers",
    "partners", "affiliates", "resellers", "vendors",
    "docs", "documentation", "api-docs", "api-v1", "api-v2",
    "v1", "v2", "v3", "latest", "old", "new",
    "mobile", "m", "touch", "iphone", "android",
    "ipad", "tablet", "responsive", "amp",
    "wordpress", "wp", "wp-admin", "wp-content", "wp-includes",
    "drupal", "joomla", "magento", "shopify", "woocommerce",
    "jenkins", "travis", "circleci", "gitlab-ci", "github-actions",
    "sonar", "sonarqube", "codeclimate", "coveralls",
    "sentry", "rollbar", "loggly", "papertrail", "logentries",
    "pagerduty", "opsgenie", "victorops",
    "autodiscover", "msoid", "lyncdiscover",
    "enterpriseenrollment", "enterpriseregistration",
]

def _resolve(hostname, timeout=3):
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except socket.gaierror:
        return None

def dns_bruteforce(domain: str, wordlist: str = None, max_workers: int = 20, timeout: int = 5) -> str:
    """
    Bruteforce subdomains of a given domain using DNS resolution.
    
    Parameters:
    - domain: The target domain (e.g. 'example.com')
    - wordlist: Comma-separated list of subdomain words. Defaults to 150 built-in.
    - max_workers: Number of concurrent resolver threads
    - timeout: DNS resolution timeout in seconds
    """
    domain = domain.lower().strip()
    if domain.startswith("http://") or domain.startswith("https://"):
        from urllib.parse import urlparse
        domain = urlparse(domain).netloc or urlparse(domain).hostname
    
    if wordlist:
        words = [w.strip() for w in wordlist.split(",") if w.strip()]
    else:
        words = SUBDOMAIN_WORDLIST
    
    found = []
    
    def check_word(word):
        hostname = f"{word}.{domain}"
        ip = _resolve(hostname, timeout)
        if ip:
            return (word, hostname, ip)
        return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_word, w): w for w in words}
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result:
                    found.append(result)
            except:
                pass
    
    found.sort(key=lambda x: x[0])
    
    lines = [f"DNS Subdomain Scan: {domain}", "=" * 50]
    if not found:
        lines.append("No subdomains discovered.")
    else:
        lines.append(f"{'SUBDOMAIN':<25} {'HOSTNAME':<40} {'IP':<20}")
        lines.append("-" * 80)
        for word, hostname, ip in found:
            lines.append(f"{word:<25} {hostname:<40} {ip:<20}")
        lines.append(f"\nTotal discovered: {len(found)} subdomains")
    
    return "\n".join(lines)
