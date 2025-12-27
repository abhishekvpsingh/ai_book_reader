import sys
import httpx

base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

resp = httpx.get(f"{base_url}/health", timeout=5)
resp.raise_for_status()
print("health:", resp.json())
