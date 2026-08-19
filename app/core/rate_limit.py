from slowapi import Limiter
from slowapi.util import get_remote_address

# headers_enabled=True faz o slowapi anexar Retry-After/X-RateLimit-* nas respostas
# (inclusive nas 429, via app.main.rate_limit_handler) em vez de só no corpo.
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
