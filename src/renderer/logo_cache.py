from PIL import Image

class LogoCache:
    _instance = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogoCache, cls).__new__(cls)
        return cls._instance

    def get(self, key):
        """Get a logo from cache using a unique key"""
        return self._cache.get(key)

    def set(self, key, logo):
        """Store a logo in cache with a unique key"""
        self._cache[key] = logo

    def clear(self):
        """Clear the entire cache"""
        self._cache.clear() 