import hashlib
from django.core.cache import cache

class CacheService:
    @staticmethod
    def _make_key(prefix, *args):
        """Generate a clean, hashed cache key."""
        raw_key = ":".join(str(arg).strip().lower() for arg in args)
        hashed = hashlib.md5(raw_key.encode('utf-8')).hexdigest()
        return f"{prefix}:{hashed}"

    @classmethod
    def get_cached_route(cls, start, finish):
        """Retrieve route data from cache."""
        key = cls._make_key("route", start, finish)
        return cache.get(key)

    @classmethod
    def cache_route(cls, start, finish, route_data, timeout=86400):
        """Save route data to cache. Default timeout is 24 hours."""
        key = cls._make_key("route", start, finish)
        cache.set(key, route_data, timeout)

    @classmethod
    def get_cached_geocode(cls, query):
        """Retrieve coordinates from cache."""
        key = cls._make_key("geocode", query)
        return cache.get(key)

    @classmethod
    def cache_geocode(cls, query, coords, timeout=604800):
        """Save coordinates to cache. Default timeout is 7 days."""
        key = cls._make_key("geocode", query)
        cache.set(key, coords, timeout)
