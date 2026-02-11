import fastapi as fa
import geoip2.database
import geoip2.errors

GEOIP_DB_PATH = "/etc/geoip/GeoLite2-Country.mmdb"


def get_client_ip(request: fa.Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def get_country_code(ip: str) -> str | None:
    try:
        with geoip2.database.Reader(GEOIP_DB_PATH) as reader:
            response = reader.country(ip)
            return response.country.iso_code
    except (geoip2.errors.AddressNotFoundError, FileNotFoundError, ValueError):
        return None
