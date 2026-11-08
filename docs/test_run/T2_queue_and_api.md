# T2: Queue and API Test Run

- **Date/Time**: 2026-11-07 16:10 IST
- **Session Baseline Real Gnani Calls**: 272
- **Calls at end of T2**: 279
- **Calls used in T2**: 7
- **Calls used since baseline**: 7 / 400

---

## Test Results Summary

| # | Test | Expected | Actual | Result | Evidence |
|---|------|----------|--------|--------|----------|
| 1 | Book today, book tomorrow, token numbers increase correctly | Tokens numbered sequentially starting at 1 per date (`Today=[1, 2]`, `Tomorrow=[1, 2]`) | `Today=[1, 2]` (`2026-11-07`), `Tomorrow=[1, 2]` (`2026-11-08`) | **PASS** | `POST /tokens` returns HTTP 201 with numbers 1, 2 on today and 1, 2 on tomorrow |
| 2 | Book twice by same session (duplicate rule) | Client receives newest token; sequential number allocated | Token #3 allocated, then Token #4 allocated with status `waiting` | **PASS** | `POST /text/turn` yields token_number=3 then 4; client retains latest token ID 6 |
| 3 | Book after cancel | Cancelled token stays cancelled; new booking gets next sequential number with status `waiting` | Token #4 transitioned to `cancelled`; new booking allocated Token #5 with status `waiting` | **PASS** | `POST /text/turn` (intent=YES) sets status `cancelled`; next `POST /text/turn` (intent=BOOK) creates token_id=7 (#5) `waiting` |
| 4 | Status: position and ahead count | Token #1 ahead=0, Token #2 ahead=1, Token #3 ahead=2 | `ahead_count`: #1=0, #2=1, #3=2 | **PASS** | `GET /tokens/{id}` returns accurate `ahead_count` and `position` in active queue |
| 5 | Cancel: asks confirmation; yes cancels; no keeps; token freed | First cancel prompts confirmation; "no" keeps token `waiting`; "yes" sets token to `cancelled` | First prompt asks confirmation; "no" keeps Token #4 `waiting`; "yes" changes status to `cancelled` | **PASS** | `turn_diagnostic`: intent=CANCEL prompts confirmation; intent=NO retains `waiting`; intent=YES sets `cancelled` |
| 6 | Staff operations: Call next, Mark done, No-show | State changes: `waiting` -> `in_consult` -> `done`; `waiting` -> `in_consult` -> `no_show` | Token #1 transitions `waiting` -> `in_consult` -> `done`; Token #2 transitions `waiting` -> `in_consult` -> `no_show` | **PASS** | `POST /queue/next` (200), `POST /queue/1/done` (200), `POST /queue/next` (200), `POST /queue/2/no-show` (200) |
| 7 | Seed Demo Data and Reset Demo | `/demo/seed` creates 5 sample tokens; `/demo/reset` wipes queue and resets count to 0 | Seeded 5 tokens; Reset restored `total_tokens=0` and empty active queue | **PASS** | `POST /demo/seed` status 200, `GET /queue` returns 5 tokens; `POST /demo/reset` status 200, `GET /queue` returns 0 tokens |
| 8 | Status or cancel with no token; stale token after reset | Safe error message without crash; stale token lookup returns HTTP 404 | Status/cancel return "No active token was found for you"; `GET /tokens/999999` returns HTTP 404 | **PASS** | `POST /text/turn` status 200 with fallback message; `GET /tokens/999999` returns 404 `{"detail": "token_not_found"}` |
| 9 | Today/Tomorrow separation, empty queue, large queue (50 bookings) | 0 bookings in today's queue; 50 sequential tokens (1..50) in tomorrow's queue | Today queue: 0 tokens; Tomorrow queue: 50 tokens (tokens #1 through #50) | **PASS** | `GET /queue?appointment_date=2026-11-08` returns `total_tokens: 50`, `active_tokens: 50`; today queue remains 0 |
| 10 | Concurrent requests (10 at once) give unique token numbers | 10 distinct, unique sequential token numbers allocated without collision | Only 3 unique numbers allocated: `[1, 1, 1, 2, 2, 2, 2, 2, 2, 3]` | **FAIL** | Race condition in `backend/app/services/queue_service.py` where `SELECT coalesce(max(number), 0) + 1` executes across threads without SQLite table write lock |
| 11 | WebSocket: every change sends an event to the dashboard | Events broadcasted to dashboard WebSocket connection on queue state mutations | TestClient synthetic test harness did not capture events (`captured events = []`) | **FAIL** | `backend/app/routers/websocket_router.py`: `asyncio.create_task` broadcast coroutines in in-process `TestClient` lack a running persistent event loop |
| 12 | Same token number appears in reply text, English line, card, feed | Consistent token number across all output channels | Token number #1 consistent across `token.number` (1), `reply_text` ("...number one..."), `english_translation` ("...number 1..."), and `voice_logs.token_id` (1) | **PASS** | Response payload and database record contain identical token number 1 |
| 13 | Times shown in IST, stored in UTC | Database stores UTC timestamp; `format_ist_time` renders IST string | Stored UTC: `2026-11-07T10:39:50.353801`; Rendered IST: `'4:09 PM'` (differs from zero-padded `'04:09 PM'`) | **FAIL** | `backend/app/services/turn_service.py:format_ist_time()` formats hour without zero-padding (`%I` vs `%-I`) |

---

## Bugs Discovered & Documented

1. **Concurrent Token Number Collision**:
   - **File**: `backend/app/services/queue_service.py`
   - **Evidence**: 10 concurrent requests yielded duplicate numbers: `[1, 1, 1, 2, 2, 2, 2, 2, 2, 3]`.
   - **Cause**: Non-atomic calculation `SELECT coalesce(max(number), 0) + 1` without database table-level exclusion locking.
2. **Dynamic TTS Call in /text/turn**:
   - **File**: `backend/app/services/turn_service.py`
   - **Evidence**: `gnani_usage` increased by 7 real calls during text turn tests because dynamic booking sentences bypass cache and invoke `synthesize_reply_audio()`.
3. **IST Time String Zero-Padding**:
   - **File**: `backend/app/services/turn_service.py` (`format_ist_time()`)
   - **Evidence**: Formatted IST returned `'4:09 PM'` instead of `'04:09 PM'`.

