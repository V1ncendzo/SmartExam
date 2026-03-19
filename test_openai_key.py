import requests
import os

api_key = os.environ.get("GEMINI_API_KEY", "")
print(f"Key prefix: {api_key[:15]}...")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
payload = {
    "contents": [{"role": "user", "parts": [{"text": "Say: OK"}]}]
}

res = requests.post(url, json=payload, timeout=15)
data = res.json()
print(f"Status: {res.status_code}")
if "error" in data:
    print(f"ERROR: {data['error']['message']}")
else:
    print(f"SUCCESS: {data['candidates'][0]['content']['parts'][0]['text']}")
