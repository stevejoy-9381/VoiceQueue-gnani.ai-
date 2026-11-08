import subprocess
import time
import sys
from pathlib import Path
import sqlite3

def get_real_calls():
    conn = sqlite3.connect('voicequeue.db')
    c = conn.cursor()
    c.execute('SELECT count(*) FROM gnani_usage WHERE cached = 0')
    val = c.fetchone()[0]
    conn.close()
    return val

test_files = sorted([f.name for f in Path('backend/tests').glob('test_*.py')])

results = []
baseline_calls = get_real_calls()
print(f"Starting test execution. Baseline real calls: {baseline_calls}")

for tf in test_files:
    test_path = f"backend/tests/{tf}"
    t0 = time.perf_counter()
    calls_before = get_real_calls()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-x", "-q", "--tb=short"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        elapsed = round(time.perf_counter() - t0, 2)
        calls_after = get_real_calls()
        calls_diff = calls_after - calls_before
        
        output = proc.stdout + proc.stderr
        exit_code = proc.returncode
        
        # Parse pytest output
        passed = 0
        failed = 0
        skipped = 0
        
        # Look for summary line e.g. "5 passed in 0.42s"
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        last_line = lines[-1] if lines else ""
        
        results.append({
            "file": tf,
            "exit_code": exit_code,
            "elapsed": elapsed,
            "calls_made": calls_diff,
            "summary": last_line,
            "output": output
        })
        print(f"[{'PASS' if exit_code == 0 else 'FAIL'}] {tf} ({elapsed}s, calls={calls_diff}) -> {last_line}")
        
    except subprocess.TimeoutExpired:
        elapsed = 60.0
        results.append({
            "file": tf,
            "exit_code": -1,
            "elapsed": elapsed,
            "calls_made": 0,
            "summary": "TIMEOUT (>60s)",
            "output": "Test timed out after 60 seconds"
        })
        print(f"[TIMEOUT] {tf} (>60s)")

calls_end = get_real_calls()
print(f"\nCompleted {len(results)} files. Total real calls made: {calls_end - baseline_calls}")

# Output summary table format
print("\n" + "="*80)
print(f"{'File':<35} | {'Status':<6} | {'Time (s)':<8} | {'Gnani Calls':<11} | {'Pytest Output'}")
print("="*80)
for r in results:
    status_str = "PASS" if r['exit_code'] == 0 else "FAIL"
    print(f"{r['file']:<35} | {status_str:<6} | {r['elapsed']:<8} | {r['calls_made']:<11} | {r['summary']}")
print("="*80)

