import urllib.request, json

# Get a token
data = json.dumps({"username": "admin", "password": "Admin@GoaConnect1"}).encode()
req = urllib.request.Request("http://localhost:8000/api/v1/auth/login", data=data, headers={"Content-Type": "application/json"})
resp = json.loads(urllib.request.urlopen(req).read())
token = resp["access_token"]

# Semantic search
req2 = urllib.request.Request(
    "http://localhost:8000/api/v1/tourism/places?q=waterfall+nature&semantic=true",
    headers={"Authorization": f"Bearer {token}"}
)
places = json.loads(urllib.request.urlopen(req2).read())
print("Semantic search: waterfall+nature")
for p in places[:5]:
    print(f"  {p['name']} ({p['category']})")

# Travel assistant
body = json.dumps({"query": "I want beaches and forts", "days": 3, "budget_inr": 10000}).encode()
req3 = urllib.request.Request(
    "http://localhost:8000/api/v1/tourism/assistant",
    data=body,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
)
result = json.loads(urllib.request.urlopen(req3).read())
print("\nTravel assistant response:")
print(f"  agent_model: {result['agent_model']}")
print(f"  llm_available: {result['llm_available']}")
print(f"  response[:100]: {result['response'][:100].encode('ascii', errors='replace').decode()}")
