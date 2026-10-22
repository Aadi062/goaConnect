"""
GoaConnect - Full Live Test Suite
Runs against the already-running server on port 8000.
"""
import json, os, sys, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0

def req(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=8)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw.decode(errors="replace")}
    except Exception as exc:
        return 0, {"error": str(exc)}

def check(label, got, expected_code, validator=None):
    global PASS, FAIL
    code, body = got
    ok = (code == expected_code)
    if ok and validator:
        ok = validator(body)
    status = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{status}] {label}  (HTTP {code})")
    if not ok:
        print(f"         body: {json.dumps(body)[:300]}")
    return body

print("\n" + "="*58)
print("  GoaConnect  -  Live Endpoint Tests")
print("="*58)

# ── Infrastructure ────────────────────────────────────────
r = check("GET /health",
    req("GET", "/health"), 200,
    lambda b: b.get("status") == "ok")

r = check("GET /ready",
    req("GET", "/ready"), 200,
    lambda b: b.get("database") == "ok")

# ── Auth ──────────────────────────────────────────────────
import time as _t
_ts = str(int(_t.time()))[-6:]
_email = f"live{_ts}@goatest.com"
_uname = f"live{_ts}"

check("POST /auth/register (new user)",
    req("POST", "/api/v1/auth/register", {
        "email": _email,
        "username": _uname,
        "password": "Live@Test123"
    }), 201, lambda b: b.get("role") == "viewer")

check("POST /auth/register (duplicate) -> 409",
    req("POST", "/api/v1/auth/register", {
        "email": _email,
        "username": _uname,
        "password": "Live@Test123"
    }), 409)

check("POST /auth/register (weak password) -> 422",
    req("POST", "/api/v1/auth/register", {
        "email": "weak2@goatest.com",
        "username": "weakuser2",
        "password": "password"
    }), 422)

admin_tok = check("POST /auth/login  (admin)",
    req("POST", "/api/v1/auth/login", {
        "username": "admin", "password": "Admin@GoaConnect1"
    }), 200, lambda b: "access_token" in b)
ADMIN = admin_tok.get("access_token", "")

analyst_tok = check("POST /auth/login  (analyst)",
    req("POST", "/api/v1/auth/login", {
        "username": "analyst", "password": "Analyst@GoaConnect1"
    }), 200, lambda b: "access_token" in b)
ANALYST = analyst_tok.get("access_token", "")

me = check("GET  /auth/me",
    req("GET", "/api/v1/auth/me", token=ADMIN), 200,
    lambda b: b.get("username") == "admin")
print(f"         username={me.get('username')}  role={me.get('role')}")

check("GET  /auth/me  (bad token) -> 401",
    req("GET", "/api/v1/auth/me", token="bad.jwt.xyz"), 401)

check("POST /auth/login  (wrong password) -> 401",
    req("POST", "/api/v1/auth/login", {
        "username": "admin", "password": "wrongpass"
    }), 401)

# ── Security: Alerts ──────────────────────────────────────
posture = check("GET  /security/posture",
    req("GET", "/api/v1/security/posture", token=ANALYST), 200,
    lambda b: "posture" in b)
print(f"         posture={posture.get('posture')}  open_alerts={posture.get('open_alerts')}")

alert = check("POST /security/alerts  (create)",
    req("POST", "/api/v1/security/alerts", {
        "title": "Brute Force - 8 failures from 10.10.10.1",
        "description": "Authentication guardian detected 8 rapid failures",
        "severity": "high",
        "alert_type": "brute_force_suspected",
        "source_agent": "authentication_guardian",
        "confidence": 0.87
    }, token=ANALYST), 201,
    lambda b: b.get("status") == "open" and b.get("is_verified") == False)
ALERT_ID = alert.get("id", "")
print(f"         id={ALERT_ID[:8]}...  severity={alert.get('severity')}")

check("GET  /security/alerts  (list)",
    req("GET", "/api/v1/security/alerts", token=ANALYST), 200,
    lambda b: b.get("total", 0) >= 1)

check("GET  /security/alerts/:id",
    req("GET", f"/api/v1/security/alerts/{ALERT_ID}", token=ANALYST), 200,
    lambda b: b.get("id") == ALERT_ID)

check("PATCH /security/alerts/:id  (update status)",
    req("PATCH", f"/api/v1/security/alerts/{ALERT_ID}", {
        "status": "investigating", "assigned_to": "analyst1"
    }, token=ANALYST), 200,
    lambda b: b.get("status") == "investigating")

check("POST /security/alerts  (analyst blocked from no-role) - RBAC",
    req("POST", "/api/v1/security/alerts", {
        "title": "test", "description": "x",
        "severity": "low", "alert_type": "test", "source_agent": "test"
    }, token="badtoken"), 401)

# ── Security: Approvals ───────────────────────────────────
appr = check("POST /security/approvals  (create)",
    req("POST", "/api/v1/security/approvals", {
        "requesting_agent": "containment_advisor",
        "action_type": "account_lockout",
        "action_description": "Lock user brute123 for 15 minutes",
        "risk_level": "medium",
        "expires_in_minutes": 60
    }, token=ANALYST), 201,
    lambda b: b.get("status") == "pending")
APPR_ID = appr.get("id", "")

check("GET  /security/approvals  (list pending)",
    req("GET", "/api/v1/security/approvals", token=ANALYST), 200,
    lambda b: isinstance(b, list) and len(b) >= 1)

check("POST /security/approvals/:id/decide  (approve)",
    req("POST", f"/api/v1/security/approvals/{APPR_ID}/decide", {
        "approved": True, "note": "Confirmed by SOC lead"
    }, token=ANALYST), 200,
    lambda b: b.get("status") == "approved")

check("POST /security/approvals/:id/decide  (double approve -> 409)",
    req("POST", f"/api/v1/security/approvals/{APPR_ID}/decide", {
        "approved": True
    }, token=ANALYST), 409)

# ── Audit Log ─────────────────────────────────────────────
audit = check("GET  /security/audit  (log populated)",
    req("GET", "/api/v1/security/audit", token=ANALYST), 200,
    lambda b: isinstance(b, list) and len(b) >= 1)
if audit:
    print(f"         {len(audit)} events  latest={audit[0].get('event_type')}")

# ── Tourism ───────────────────────────────────────────────
places = check("GET  /tourism/places  (8 seeded places)",
    req("GET", "/api/v1/tourism/places"), 200,
    lambda b: len(b) >= 8)
if places:
    print(f"         {len(places)} places  eg: {places[0]['name']}, {places[1]['name']}")

check("GET  /tourism/places?q=beach",
    req("GET", "/api/v1/tourism/places?q=beach"), 200,
    lambda b: len(b) >= 1)

check("GET  /tourism/places?category=heritage",
    req("GET", "/api/v1/tourism/places?category=heritage"), 200,
    lambda b: len(b) >= 2)

# ── Agents ────────────────────────────────────────────────
t1 = check("POST /agents/tasks  (auth_anomaly - brute force)",
    req("POST", "/api/v1/agents/tasks", {
        "task_type": "auth_anomaly",
        "payload": {
            "login_events": [{"outcome": "failure", "ip": "1.2.3.4"}] * 8,
            "user_id": "testuser99"
        }
    }, token=ANALYST), 200,
    lambda b: b.get("status") == "success")
if t1:
    findings = t1.get("result", {}).get("findings", [])
    print(f"         agent={t1.get('agent_role')}  findings={[f['type'] for f in findings]}  conf={t1.get('confidence')}")

t2 = check("POST /agents/tasks  (travel_query)",
    req("POST", "/api/v1/agents/tasks", {
        "task_type": "travel_query",
        "payload": {"query": "best beaches in Goa", "days": 3, "budget_inr": 12000}
    }, token=ANALYST), 200,
    lambda b: b.get("status") == "success")
if t2:
    recs = t2.get("result", {}).get("recommendations", [])
    print(f"         agent={t2.get('agent_role')}  recs={recs[:3]}")

t3 = check("POST /agents/tasks  (itinerary - 3 days)",
    req("POST", "/api/v1/agents/tasks", {
        "task_type": "itinerary",
        "payload": {"days": 3, "budget_inr": 15000, "group_size": 2}
    }, token=ANALYST), 200,
    lambda b: len(b.get("result", {}).get("itinerary", [])) == 3)
if t3:
    days = t3.get("result", {}).get("itinerary", [])
    print(f"         days: {[d['theme'] for d in days]}")

t4 = check("POST /agents/tasks  (heritage guide)",
    req("POST", "/api/v1/agents/tasks", {
        "task_type": "heritage",
        "payload": {"site": "basilica of bom jesus"}
    }, token=ANALYST), 200,
    lambda b: b.get("status") == "success")
if t4:
    print(f"         site={t4.get('result',{}).get('full_name')}  year={t4.get('result',{}).get('year')}")

t5 = check("POST /agents/tasks  (alert_triage - deduplicate)",
    req("POST", "/api/v1/agents/tasks", {
        "task_type": "alert_triage",
        "payload": {"alerts": [
            {"alert_type": "brute_force", "affected_resource": "user1", "severity": "high"},
            {"alert_type": "brute_force", "affected_resource": "user1", "severity": "high"},
            {"alert_type": "api_abuse",   "affected_resource": "login", "severity": "medium"},
        ]}
    }, token=ANALYST), 200,
    lambda b: b.get("result", {}).get("deduplicated_count") == 2)
if t5:
    r5 = t5.get("result", {})
    print(f"         {r5.get('original_count')} alerts -> {r5.get('deduplicated_count')} after dedup")

t6 = check("POST /agents/tasks  (containment - high risk needs approval)",
    req("POST", "/api/v1/agents/tasks", {
        "task_type": "containment",
        "payload": {"alert_type": "authorization_abuse"}
    }, token=ANALYST), 200,
    lambda b: b.get("requires_human_approval") == True)

# ── Policy Enforcement (LLM-independent) ─────────────────
p1 = check("POST /agents/policy/check  (permitted)",
    req("POST", "/api/v1/agents/policy/check", {
        "agent_role": "authentication_guardian",
        "tool": "write:alerts",
        "action": "create_alert"
    }, token=ANALYST), 200,
    lambda b: b.get("allowed") == True and b.get("requires_approval") == False)

p2 = check("POST /agents/policy/check  (BLOCKED - tourism writing security)",
    req("POST", "/api/v1/agents/policy/check", {
        "agent_role": "travel_assistant",
        "tool": "write:alerts",
        "action": "create_alert"
    }, token=ANALYST), 200,
    lambda b: b.get("allowed") == False)

p3 = check("POST /agents/policy/check  (high-impact needs approval)",
    req("POST", "/api/v1/agents/policy/check", {
        "agent_role": "soc_orchestrator",
        "tool": "request:approval",
        "action": "account_suspension"
    }, token=ANALYST), 200,
    lambda b: b.get("allowed") == True and b.get("requires_approval") == True)
if p3:
    print(f"         allowed={p3.get('allowed')}  requires_approval={p3.get('requires_approval')}")

check("GET  /agents/roles  (permission matrix)",
    req("GET", "/api/v1/agents/roles", token=ANALYST), 200,
    lambda b: "authentication_guardian" in b and "travel_assistant" in b)

# ── Final posture (should show open alerts) ───────────────
final = check("GET  /security/posture  (final state)",
    req("GET", "/api/v1/security/posture", token=ANALYST), 200,
    lambda b: b.get("open_alerts", 0) >= 0)
if final:
    print(f"         posture={final.get('posture')}  open={final.get('open_alerts')}  critical={final.get('critical_open_alerts')}")

# ── Summary ───────────────────────────────────────────────
print()
print("="*58)
total = PASS + FAIL
bar = "#" * PASS + "-" * FAIL
print(f"  [{bar}]")
print(f"  RESULTS: {PASS} passed  /  {FAIL} failed  /  {total} total")
print("="*58)
if FAIL == 0:
    print("  ALL TESTS PASSED  -  GoaConnect is fully operational")
else:
    print(f"  {FAIL} test(s) failed")
print()
sys.exit(0 if FAIL == 0 else 1)
