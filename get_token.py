import json, requests, webbrowser
from urllib.parse import urlparse, parse_qs

REDIRECT = "https://localhost:8080"      # must match the Yahoo app exactly

s = json.load(open("yahoo_secrets.json"))

# 1. Open the Yahoo approval page in your browser.
auth_url = (
    "https://api.login.yahoo.com/oauth2/request_auth"
    f"?client_id={s['client_id']}&redirect_uri={REDIRECT}&response_type=code"
)
print("Opening browser. Log in and approve.")
webbrowser.open(auth_url)

print("\nYour browser will land on a page that won't load. That's normal.")
print("Copy the WHOLE address from the address bar and paste it below.\n")

# 2. Pull the one-time code out of whatever they paste.
pasted = input("Paste it here: ").strip()
code = parse_qs(urlparse(pasted).query).get("code", [pasted])[0]

# 3. Trade that code for tokens.
r = requests.post(
    "https://api.login.yahoo.com/oauth2/get_token",
    data={
        "client_id": s["client_id"],
        "client_secret": s["client_secret"],
        "redirect_uri": REDIRECT,
        "code": code,
        "grant_type": "authorization_code",
    },
)
r.raise_for_status()

# 4. Save the key card.
json.dump(r.json(), open("yahoo_token.json", "w"), indent=2)
print("Saved yahoo_token.json — you're done with this file forever.")