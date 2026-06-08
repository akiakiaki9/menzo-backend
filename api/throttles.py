from rest_framework.throttling import SimpleRateThrottle


class FormRateThrottle(SimpleRateThrottle):
    """Throttle for frontend forms (per-IP).

    Uses DRF's DEFAULT_THROTTLE_RATES with scope 'form'.
    Rate configured in settings as '4/min'.
    """
    scope = 'form'

    def get_cache_key(self, request, view):
        # Use IP-based throttling. If behind proxy, consider X-Forwarded-For.
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
