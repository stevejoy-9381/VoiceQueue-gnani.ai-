"""Comprehensive T2 Queue and API Verification Script.

Tests every queue rule and endpoint directly using FastAPI TestClient with stubs.
Zero real calls to Gnani API.
"""

import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db import get_db, SessionLocal
from backend.app.models import Token, VoiceLog, GnaniUsage
from backend.app.services import queue_service, turn_service

client = TestClient(app)

def get_real_gnani_calls():
    conn = sqlite3.connect("voicequeue.db")
    c = conn.cursor()
    c.execute("SELECT count(*) FROM gnani_usage WHERE cached = 0")
    val = c.fetchone()[0]
    conn.close()
    return val

baseline_real_calls = get_real_gnani_calls()
results = []

def record(test_name, expected, actual, passed, evidence=""):
    results.append({
        "test": test_name,
        "expected": expected,
        "actual": actual,
        "result": "PASS" if passed else "FAIL",
        "evidence": evidence
    })
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {test_name}: {actual} ({evidence})")

# Reset demo first to start clean
client.post("/demo/reset")

# 1. Book today, book tomorrow, token numbers increase correctly
res_t1 = client.post("/tokens", json={"day": "today", "language": "te-IN"}).json()
res_t2 = client.post("/tokens", json={"day": "today", "language": "te-IN"}).json()
res_m1 = client.post("/tokens", json={"day": "tomorrow", "language": "en-IN"}).json()
res_m2 = client.post("/tokens", json={"day": "tomorrow", "language": "en-IN"}).json()

t_nums = [res_t1["number"], res_t2["number"]]
m_nums = [res_m1["number"], res_m2["number"]]
pass_1 = (t_nums == [1, 2] and m_nums == [1, 2] and res_t1["date"] != res_m1["date"])
record(
    "Book today & tomorrow sequential numbering",
    "Today=[1, 2], Tomorrow=[1, 2], distinct dates",
    f"Today={t_nums}, Tomorrow={m_nums}",
    pass_1,
    f"Today date={res_t1['date']}, Tomorrow date={res_m1['date']}"
)

# 2. Book twice by same session (duplicate rule)
# Each turn books sequential token, client tracks newest token
res_sess1 = client.post("/text/turn", json={"text": "repu token kavali", "language": "te", "session_id": "sess_dup_test"}).json()
res_sess2 = client.post("/text/turn", json={"text": "repu token kavali", "language": "te", "session_id": "sess_dup_test"}).json()
tok1_num = res_sess1["token"]["number"]
tok2_num = res_sess2["token"]["number"]
pass_2 = (tok2_num == tok1_num + 1 and res_sess2["token"]["status"] == "waiting")
record(
    "Book twice by same session",
    "Successive booking allocates next token number (newest held by client)",
    f"First token={tok1_num}, Second token={tok2_num}",
    pass_2,
    f"Token #{tok2_num} allocated with status waiting"
)

# 3. Book after cancel
# Cancel token from sess2, then book again
cancel_req = client.post("/text/turn", json={"text": "token cancel cheyandi", "language": "te", "session_id": "sess_cancel_book", "token_id": res_sess2["token"]["id"]}).json()
cancel_confirm = client.post("/text/turn", json={"text": "yes", "language": "te", "session_id": "sess_cancel_book"}).json()
book_after = client.post("/text/turn", json={"text": "repu token kavali", "language": "te", "session_id": "sess_cancel_book"}).json()
pass_3 = (cancel_confirm["token"]["status"] == "cancelled" and book_after["token"]["status"] == "waiting" and book_after["token"]["id"] != res_sess2["token"]["id"])
record(
    "Book after cancel",
    "Cancelled token status=cancelled, subsequent booking succeeds with new token",
    f"Cancelled status={cancel_confirm['token']['status']}, New token status={book_after['token']['status']}",
    pass_3,
    f"New token #{book_after['token']['number']} (id={book_after['token']['id']})"
)

# 4. Status: position and ahead in queue count are correct
client.post("/demo/reset")
t_a = client.post("/tokens", json={"day": "today"}).json() # #1
t_b = client.post("/tokens", json={"day": "today"}).json() # #2
t_c = client.post("/tokens", json={"day": "today"}).json() # #3

# t_a is position 1, ahead = 0
# t_b is position 2, ahead = 1
# t_c is position 3, ahead = 2
stat_a = client.get(f"/tokens/{t_a['id']}").json()
stat_b = client.get(f"/tokens/{t_b['id']}").json()
stat_c = client.get(f"/tokens/{t_c['id']}").json()

pass_4 = (stat_a["ahead_count"] == 0 and stat_b["ahead_count"] == 1 and stat_c["ahead_count"] == 2)
record(
    "Queue position and ahead_count accuracy",
    "Token #1 ahead=0, Token #2 ahead=1, Token #3 ahead=2",
    f"#1 ahead={stat_a['ahead_count']}, #2 ahead={stat_b['ahead_count']}, #3 ahead={stat_c['ahead_count']}",
    pass_4,
    f"Positions verified in today's active line"
)

# 5. Cancel: asks confirmation; yes cancels; no keeps; token freed
sess_c_id = "sess_cancel_confirm_test"
tok_test = client.post("/tokens", json={"day": "today"}).json()
req_cancel = client.post("/text/turn", json={"text": "cancel my token", "language": "en", "session_id": sess_c_id, "token_id": tok_test["id"]}).json()
has_prompt = req_cancel["pending_confirm"] and "cancel" in req_cancel["reply_text"].lower()

# Case 5a: No keeps token
abort_cancel = client.post("/text/turn", json={"text": "no", "language": "en", "session_id": sess_c_id}).json()
tok_after_no = client.get(f"/tokens/{tok_test['id']}").json()
pass_5a = (has_prompt and not abort_cancel["pending_confirm"] and tok_after_no["status"] == "waiting")

# Case 5b: Re-request and yes cancels
req_cancel2 = client.post("/text/turn", json={"text": "cancel my token", "language": "en", "session_id": sess_c_id, "token_id": tok_test["id"]}).json()
confirm_cancel2 = client.post("/text/turn", json={"text": "yes", "language": "en", "session_id": sess_c_id}).json()
tok_after_yes = client.get(f"/tokens/{tok_test['id']}").json()
pass_5b = (tok_after_yes["status"] == "cancelled")

record(
    "Cancel confirmation flow (Yes cancels, No keeps)",
    "Prompt on cancel -> No preserves token -> Yes cancels token",
    f"Prompt={has_prompt}, After No={tok_after_no['status']}, After Yes={tok_after_yes['status']}",
    pass_5a and pass_5b,
    f"Token #{tok_test['number']} state transition verified"
)

# 6. Call next, Mark done, No-show: states and counts update
client.post("/demo/reset")
tok_1 = client.post("/tokens", json={"day": "today"}).json()
tok_2 = client.post("/tokens", json={"day": "today"}).json()
tok_3 = client.post("/tokens", json={"day": "today"}).json()

# Call next moves tok_1 to in_consult
next_1 = client.post("/queue/next?day=today").json()
# Mark done marks tok_1 done
done_1 = client.post(f"/queue/{tok_1['id']}/done").json()
# Call next moves tok_2 to in_consult
next_2 = client.post("/queue/next?day=today").json()
# Mark no-show marks tok_2 no_show
noshow_2 = client.post(f"/queue/{tok_2['id']}/no-show").json()

pass_6 = (
    next_1["status"] == "in_consult" and next_1["id"] == tok_1["id"] and
    done_1["status"] == "done" and
    next_2["status"] == "in_consult" and next_2["id"] == tok_2["id"] and
    noshow_2["status"] == "no_show"
)
record(
    "Staff actions: Call next, Mark done, No-show",
    "tok1 in_consult -> done; tok2 in_consult -> no_show",
    f"tok1={next_1['status']}->{done_1['status']}, tok2={next_2['status']}->{noshow_2['status']}",
    pass_6,
    f"Endpoint transitions /queue/next, /done, /no-show"
)

# 7. Seed Demo Data (1-6) and Reset Demo; counts return to zero
client.post("/demo/reset")
seed_res = client.post("/demo/seed?day=today&count=5").json()
q_after_seed = client.get("/queue?day=today").json()
client.post("/demo/reset")
q_after_reset = client.get("/queue?day=today").json()

pass_7 = (len(seed_res) == 5 and q_after_seed["total_tokens"] == 5 and q_after_reset["total_tokens"] == 0)
record(
    "Seed Demo Data (5 tokens) & Reset Demo",
    "Seed creates 5 tokens, Reset returns total_tokens to 0",
    f"Seeded={len(seed_res)}, After reset total_tokens={q_after_reset['total_tokens']}",
    pass_7,
    "POST /demo/seed and POST /demo/reset verified"
)

# 8. Status or cancel with no token; stale token after reset (no 404 polling loop)
client.post("/demo/reset")
status_no_tok = client.post("/text/turn", json={"text": "what is my token status", "language": "en", "session_id": "sess_no_tok"}).json()
cancel_no_tok = client.post("/text/turn", json={"text": "cancel my token", "language": "en", "session_id": "sess_no_tok"}).json()
stale_get = client.get("/tokens/999999")

pass_8 = (
    "no active token" in status_no_tok["reply_text"].lower() and
    "no active token" in cancel_no_tok["reply_text"].lower() and
    stale_get.status_code == 404
)
record(
    "Status or cancel with no token & Stale token lookup",
    "Friendly 'no active token' reply, non-existent token returns HTTP 404",
    f"Status reply='{status_no_tok['reply_text'][:30]}...', Stale HTTP={stale_get.status_code}",
    pass_8,
    "Handled safely without crashing"
)

# 9. Today/Tomorrow separation, empty queue, large queue (50 bookings)
client.post("/demo/reset")
empty_q = client.get("/queue?day=today").json()

# Book 50 tokens for tomorrow
t_ids = []
for i in range(50):
    res_b = client.post("/tokens", json={"day": "tomorrow"}).json()
    t_ids.append(res_b["number"])

q_today = client.get("/queue?day=today").json()
q_tomorrow = client.get("/queue?day=tomorrow").json()

pass_9 = (
    empty_q["total_tokens"] == 0 and
    q_today["total_tokens"] == 0 and
    q_tomorrow["total_tokens"] == 50 and
    t_ids == list(range(1, 51))
)
record(
    "Today/Tomorrow separation & Large queue (50 bookings)",
    "Today=0, Tomorrow=50 sequential numbers (1..50)",
    f"Today total={q_today['total_tokens']}, Tomorrow total={q_tomorrow['total_tokens']}, Min/Max={min(t_ids)}..{max(t_ids)}",
    pass_9,
    "Zero leakage between today and tomorrow queues"
)

# 10. Concurrent requests (10 at once) give unique token numbers
client.post("/demo/reset")
def do_book(i):
    c = TestClient(app)
    return c.post("/tokens", json={"day": "today"}).json()

with ThreadPoolExecutor(max_workers=10) as executor:
    conc_results = list(executor.map(do_book, range(10)))

conc_nums = [r["number"] for r in conc_results]
conc_unique = len(set(conc_nums)) == 10
pass_10 = (conc_unique and sorted(conc_nums) == list(range(1, 11)))
record(
    "Concurrent booking (10 simultaneous threads)",
    "All 10 tokens receive unique sequential numbers 1..10 without duplicates",
    f"Numbers allocated={sorted(conc_nums)}, Unique count={len(set(conc_nums))}",
    pass_10,
    "Thread-safe atomic sequence allocation"
)

# 11. WebSocket event emission check
from backend.app.services.connection_manager import manager
ws_events = []
class MockWS:
    async def send_json(self, msg):
        ws_events.append(msg)

mock_ws = MockWS()
manager.active_connections.append(mock_ws)

# Trigger actions
client.post("/tokens", json={"day": "today"})
client.post("/queue/next?day=today")
client.post("/demo/reset")

manager.disconnect(mock_ws)

event_types = [e.get("type") for e in ws_events]
pass_11 = ("queue_changed" in event_types and "token_called" in event_types and "demo_reset" in event_types)
record(
    "WebSocket event broadcasts to dashboard",
    "Dispatches queue_changed, token_called, demo_reset",
    f"Captured events={event_types}",
    pass_11,
    "Broadcasts verified on manager connection"
)

# 12. Same token number in reply text, English line, card, and feed
client.post("/demo/reset")
turn_rep = client.post("/text/turn", json={"text": "I need a token for tomorrow", "language": "en", "session_id": "sess_num_check"}).json()
tok_obj = turn_rep["token"]
tok_num = tok_obj["number"] # e.g. 1
tok_num_str = str(tok_num)
in_reply = (tok_num_str in turn_rep["reply_text"] or "one" in turn_rep["reply_text"].lower())
in_en_trans = (tok_num_str in turn_rep["english_translation"] or "one" in turn_rep["english_translation"].lower())

with SessionLocal() as db:
    last_vlog = db.query(VoiceLog).order_by(VoiceLog.id.desc()).first()
    vlog_num = last_vlog.token_id

pass_12 = (in_reply and in_en_trans and tok_obj["number"] == 1 and vlog_num == tok_obj["id"])
record(
    "Token number consistency across reply, translation, card, & log",
    "Token #1 matches across reply text, english translation, and voice log",
    f"Card #{tok_num}, Reply='{turn_rep['reply_text']}', EN='{turn_rep['english_translation']}'",
    pass_12,
    f"VoiceLog token_id={vlog_num}"
)

# 13. Times shown in IST, stored in UTC
with SessionLocal() as db:
    tok_time = db.query(Token).order_by(Token.id.desc()).first()
    utc_created = tok_time.created_at
    ist_str = turn_service.format_ist_time(utc_created)

# Verify IST conversion: UTC + 5:30
utc_aware = utc_created.replace(tzinfo=timezone.utc)
ist_expected = utc_aware.astimezone(ZoneInfo("Asia/Kolkata")).strftime("%I:%M %p")
pass_13 = (ist_str == ist_expected)
record(
    "Timestamp storage in UTC and presentation in IST",
    f"UTC {utc_created.strftime('%H:%M')} converted to IST (+5:30) matches formatted display",
    f"Stored UTC={utc_created.isoformat()}, Formatted IST='{ist_str}' (expected='{ist_expected}')",
    pass_13,
    "backend/app/services/turn_service.py:format_ist_time()"
)

# Final Gnani Calls Check
end_real_calls = get_real_gnani_calls()
calls_used = end_real_calls - baseline_real_calls
print(f"\nT2 Finished. Baseline calls: {baseline_real_calls}, End calls: {end_real_calls}, Used: {calls_used}")
assert calls_used == 0, f"Expected 0 Gnani calls, but {calls_used} were made!"
print("ALL T2 TESTS EXECUTED WITH ZERO GNANI CALLS.")
