import requests
import base64
import os
import functools
from upstash_redis import Redis

def token_caching(func):
    """Caches the access token in Redis for 55 minutes."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):

        try:
            cached_token = self.redis.get("mpesa_access_token")
            if cached_token:
                if isinstance(cached_token, bytes):
                    cached_token = cached_token.decode("utf-8")
                return cached_token
        except Exception as e:

            print(f"Redis unavailable, fetching fresh token: {e}")

        token = func(self, *args, **kwargs)

        try:
            self.redis.setex("mpesa_access_token", 3300, token)

        except Exception as e:
            print(f"Could not cache token in Redis: {e}")

        return token
    return wrapper

class AccessToken:
    def __init__(self):
        self.redis = Redis(
            url=os.getenv("UPSTASH_REDIS_REST_URL"),
            token=os.getenv("UPSTASH_REDIS_REST_TOKEN")
        )
        self.consumer_key = os.getenv("MPESA_CONSUMER_KEY")
        self.consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
        self.base_url = os.getenv("PRODUCTION_BASE_URL")
    
    @token_caching
    def get_access_token(self):
        
        credentials = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        token_url = (f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials")
        response = requests.get(token_url, headers={"Authorization": f"Basic {credentials}"}, timeout=30)

        response.raise_for_status()
        
        token = response.json().get("access_token")

        if not token:
            raise ValueError("Daraja did not return an access token. Check your credentials.")

        return token