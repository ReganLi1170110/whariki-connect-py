"""Standalone AI connection test.

Talks to the AI provider directly, without Flask, and prints the raw HTTP
status, headers and body. Use this when the in-app assistant fails: it shows
exactly what the provider said, which distinguishes a bad key from a network
or account problem.

Usage:
    python test_ai.py
"""
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

# Groq's API is behind Cloudflare, which blocks urllib's default user agent
# (error 1010). Send a normal browser signature instead.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
BASE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-NZ,en;q=0.9",
    "Origin": "https://console.groq.com",
    "Referer": "https://console.groq.com/",
}


def load_env_file():
    path = os.path.join(HERE, '.env')
    if not os.path.exists(path):
        print(f"No .env file found at {path}")
        return
    print(f"Reading {path}")
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and value and not os.environ.get(key):
                os.environ[key] = value


def mask(value):
    if not value:
        return "(not set)"
    return f"{value[:7]}…{value[-4:]} (length {len(value)})"


def main():
    load_env_file()

    provider = os.environ.get("AI_PROVIDER", "groq").strip().lower()
    print(f"\nProvider : {provider}")

    if provider == "gemini":
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {**BASE_HEADERS, "x-goog-api-key": key}
        body = {"contents": [{"role": "user", "parts": [{"text": "Say hello in five words."}]}]}
    else:
        key = os.environ.get("GROQ_API_KEY", "").strip()
        model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b").strip()
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {**BASE_HEADERS, "Authorization": f"Bearer {key}"}
        body = {"model": model,
                "messages": [{"role": "user", "content": "Say hello in five words."}],
                "max_tokens": 50}

    print(f"Model    : {model}")
    print(f"Key      : {mask(key)}")
    print(f"Endpoint : {url}\n")

    if not key:
        print("No API key found. Add it to the .env file, e.g.:")
        print("    GROQ_API_KEY=gsk_your_key_here")
        sys.exit(1)

    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            raw = response.read().decode("utf-8", errors="replace")
            print(f"HTTP {response.status} OK\n")
            try:
                data = json.loads(raw)
                if provider == "gemini":
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    text = data["choices"][0]["message"]["content"]
                print("The AI replied:")
                print(f"    {text.strip()}\n")
                print("SUCCESS - the AI assistant is working. It will work in the app too.")
            except Exception:
                print("Unexpected response shape. Raw body:")
                print(raw[:1500])
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code} {exc.reason}\n")
        print("Response headers:")
        for k, v in exc.headers.items():
            print(f"    {k}: {v}")
        print("\nResponse body:")
        print(raw[:2000] if raw.strip() else "    (empty)")
        print("\nWhat this usually means:")
        if exc.code == 401:
            print("    401 - the key is wrong, revoked, or has a typo.")
        elif exc.code == 403:
            if "1010" in raw:
                print("    403 / Cloudflare error 1010 - blocked by bot protection based on")
                print("    the client signature, before the request reached the API.")
                print("")
                print("    This script already sends browser-like headers. If you still see")
                print("    1010, Cloudflare is likely fingerprinting Python's TLS handshake")
                print("    rather than the headers. To confirm, run this in PowerShell -")
                print("    it makes the same call with curl instead of Python:")
                print("")
                print('        curl.exe https://api.groq.com/openai/v1/chat/completions `')
                print('          -H "Authorization: Bearer YOUR_KEY" `')
                print('          -H "Content-Type: application/json" `')
                print(f'          -d \'{{\"model\":\"{model}\",\"messages\":[{{\"role\":\"user\",\"content\":\"hi\"}}]}}\'')
                print("")
                print("    If curl succeeds and Python fails, tell the developer - the app")
                print("    can be switched to a different HTTP library. If curl also returns")
                print("    1010, the block is on your network or account, not the code.")
            else:
                print("    403 - not usually a wrong key. Common causes:")
                print("      * the provider account hasn't accepted its terms of service yet")
                print("      * the request is blocked from your region, VPN or network")
                print("      * the model isn't enabled for your account")
        elif exc.code == 404:
            print(f"    404 - the model '{model}' doesn't exist for this account.")
            print("      Set a different one in .env, e.g. GROQ_MODEL=openai/gpt-oss-20b")
        elif exc.code == 429:
            print("    429 - rate limited or out of quota. Wait, or check the plan.")
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Could not reach the provider: {exc.reason}")
        print("\nThis is a network problem rather than an API problem. Check your")
        print("internet connection, and whether a VPN, firewall or proxy is blocking it.")
        sys.exit(1)


if __name__ == "__main__":
    main()
