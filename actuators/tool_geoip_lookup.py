import urllib.request
import json
def geoip_lookup(ip: str = "") -> str:
    """Look up geolocation data for an IP address using ip-api.com."""
    try:
        if ip:
            url = f"http://ip-api.com/json/{ip}"
        else:
            url = "http://ip-api.com/json/"
        resp = urllib.request.urlopen(url, timeout=10)
        data = json.loads(resp.read().decode())
        if data.get("status") == "success":
            return (f"IP: {data.get('query')}\nCountry: {data.get('country')} ({data.get('countryCode')})\n"
                    f"Region: {data.get('regionName')}\nCity: {data.get('city')}\n"
                    f"ZIP: {data.get('zip')}\nLat/Lon: {data.get('lat')}, {data.get('lon')}\n"
                    f"ISP: {data.get('isp')}\nOrganization: {data.get('org')}")
        return f"Lookup failed: {data}"
    except Exception as e:
        return f"GeoIP lookup error: {str(e)}"