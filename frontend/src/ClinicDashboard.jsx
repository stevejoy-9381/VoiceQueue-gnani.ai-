import React, { useState, useEffect, useRef, useCallback } from 'react';
import './ClinicDashboard.css';
import { API_BASE, getWebSocketUrl } from './config.js';

function formatLanguageName(code) {
  if (!code) return '';
  const lower = code.toLowerCase().trim();
  if (lower.startsWith('te')) return 'Telugu';
  if (lower.startsWith('en')) return 'English';
  if (lower.startsWith('mix')) return 'Mix';
  return code;
}

export default function ClinicDashboard() {
  const isClean = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('clean') === '1';
  const isPresentMode = typeof window !== 'undefined' && window.location.search.includes('present=1');

  const [dayTab, setDayTab] = useState('today'); // 'today' or 'tomorrow'
  const [queueData, setQueueData] = useState(null);
  const [voiceLogs, setVoiceLogs] = useState([]);
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState('');
  const [highlightedTokenId, setHighlightedTokenId] = useState(null);

  // P2-5: Live status dot & last updated timestamp
  const [wsStatus, setWsStatus] = useState('connecting'); // 'live', 'reconnecting', 'connecting'
  const [lastUpdated, setLastUpdated] = useState(() => new Date().toLocaleTimeString());

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const prevTokensCountRef = useRef(0);

  // Fetch queue data for selected day
  const fetchQueue = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/queue?day=${dayTab}`);
      if (res.ok) {
        const data = await res.json();
        setLastUpdated(new Date().toLocaleTimeString());
        if (data.tokens && data.tokens.length > prevTokensCountRef.current) {
          const newest = data.tokens[data.tokens.length - 1];
          if (newest) {
            setHighlightedTokenId(newest.id);
            // P2-5: Highlight new token row for exactly 2 seconds
            setTimeout(() => setHighlightedTokenId(null), 2000);
          }
        }
        prevTokensCountRef.current = data.tokens ? data.tokens.length : 0;
        setQueueData(data);
      }
    } catch (e) {
      console.error('Failed to fetch queue:', e);
    } finally {
      setLoading(false);
    }
  }, [dayTab]);

  // Fetch voice logs
  const fetchVoiceLogs = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/voice-logs?limit=20`);
      if (res.ok) {
        const data = await res.json();
        setVoiceLogs(data);
      }
    } catch (e) {
      console.error('Failed to fetch voice logs:', e);
    }
  }, []);

  // Fetch usage and credits
  const fetchUsage = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/usage`);
      if (res.ok) {
        const data = await res.json();
        setUsage(data);
      }
    } catch (e) {
      console.error('Failed to fetch usage:', e);
    }
  }, []);

  // Initial and tab data fetch
  useEffect(() => {
    fetchQueue();
    fetchVoiceLogs();
    fetchUsage();
  }, [fetchQueue, fetchVoiceLogs, fetchUsage]);

  // WebSocket connection & auto-reconnect
  useEffect(() => {
    function connectWs() {
      const wsUrl = getWebSocketUrl('/ws/queue');

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsStatus('live');
        setLastUpdated(new Date().toLocaleTimeString());
      };

      ws.onmessage = (event) => {
        setLastUpdated(new Date().toLocaleTimeString());
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'queue_changed') {
            fetchQueue();
            fetchVoiceLogs();
            fetchUsage();
          } else if (msg.type === 'voice_log') {
            fetchVoiceLogs();
            fetchUsage();
          } else if (msg.type === 'demo_reset') {
            fetchQueue();
            fetchVoiceLogs();
            fetchUsage();
          }
        } catch (e) {
          fetchQueue();
          fetchVoiceLogs();
          fetchUsage();
        }
      };

      ws.onclose = () => {
        setWsStatus('reconnecting');
        reconnectTimeoutRef.current = setTimeout(connectWs, 2000);
      };

      ws.onerror = () => {
        setWsStatus('reconnecting');
        ws.close();
      };
    }

    connectWs();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [fetchQueue, fetchVoiceLogs, fetchUsage]);

  const inConsult = queueData?.current_in_consult;

  // P2-5: Keyboard shortcuts N for Call next and D for Mark done (only when no input is focused)
  useEffect(() => {
    function handleKeyDown(e) {
      const activeTag = (document.activeElement?.tagName || '').toLowerCase();
      if (
        activeTag === 'input' ||
        activeTag === 'textarea' ||
        activeTag === 'select' ||
        document.activeElement?.isContentEditable
      ) {
        return;
      }

      if ((e.key === 'n' || e.key === 'N') && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        handleCallNext();
      } else if ((e.key === 'd' || e.key === 'D') && !e.ctrlKey && !e.metaKey && !e.altKey) {
        if (inConsult?.id) {
          e.preventDefault();
          handleMarkDone(inConsult.id);
        }
      } else if (e.shiftKey && (e.key === 'R' || e.key === 'r')) {
        e.preventDefault();
        const ok = typeof window !== 'undefined' && window.confirm
          ? window.confirm('Reset demo queue and seed 4 demo patients?')
          : true;
        if (ok) {
          handleResetAndSeedDemo();
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [dayTab, inConsult]);

  async function handleResetAndSeedDemo() {
    try {
      setActionMessage('Resetting and seeding 4 demo patients (Shift+R)...');
      const res = await fetch(`${API_BASE}/demo/seed?day=${dayTab}&count=4`, { method: 'POST' });
      if (res.ok) {
        setActionMessage('Seeded 4 demo tokens.');
        fetchQueue();
        fetchVoiceLogs();
        fetchUsage();
      }
    } catch (e) {
      setActionMessage('Failed to reset and seed demo.');
    }
    setTimeout(() => setActionMessage(''), 3000);
  }

  // Action handlers
  async function handleCallNext() {
    try {
      setActionMessage('Calling next patient...');
      const res = await fetch(`${API_BASE}/queue/next?day=${dayTab}`, { method: 'POST' });
      if (res.ok) {
        const tok = await res.json();
        if (tok) {
          setActionMessage(`Called Token #${tok.number}`);
        } else {
          setActionMessage('No waiting patients in queue.');
        }
        fetchQueue();
      }
    } catch (e) {
      setActionMessage('Failed to call next token.');
    }
    setTimeout(() => setActionMessage(''), 3000);
  }

  async function handleMarkDone(tokenId) {
    try {
      const res = await fetch(`${API_BASE}/queue/${tokenId}/done`, { method: 'POST' });
      if (res.ok) {
        setActionMessage(`Token marked as Done.`);
        fetchQueue();
      }
    } catch (e) {
      setActionMessage('Failed to mark token done.');
    }
    setTimeout(() => setActionMessage(''), 3000);
  }

  async function handleMarkNoShow(tokenId) {
    try {
      const res = await fetch(`${API_BASE}/queue/${tokenId}/no-show`, { method: 'POST' });
      if (res.ok) {
        setActionMessage(`Token marked as No-Show.`);
        fetchQueue();
      }
    } catch (e) {
      setActionMessage('Failed to mark token no-show.');
    }
    setTimeout(() => setActionMessage(''), 3000);
  }

  async function handleSeedDemo() {
    try {
      setActionMessage('Seeding demo patients...');
      const res = await fetch(`${API_BASE}/demo/seed?day=${dayTab}`, { method: 'POST' });
      if (res.ok) {
        setActionMessage('Seeded demo tokens.');
        fetchQueue();
        fetchVoiceLogs();
      }
    } catch (e) {
      setActionMessage('Failed to seed demo data.');
    }
    setTimeout(() => setActionMessage(''), 3000);
  }

  async function handleResetDemo() {
    try {
      setActionMessage('Resetting demo queue...');
      const res = await fetch(`${API_BASE}/demo/reset`, { method: 'POST' });
      if (res.ok) {
        setActionMessage('Demo queue reset successfully.');
        fetchQueue();
        fetchVoiceLogs();
        fetchUsage();
      }
    } catch (e) {
      setActionMessage('Failed to reset queue.');
    }
    setTimeout(() => setActionMessage(''), 3000);
  }

  async function handleClearVoiceLogs() {
    if (!window.confirm('Are you sure you want to clear all voice activity logs?')) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/voice-logs/clear`, { method: 'POST' });
      if (res.ok) {
        setVoiceLogs([]);
        setActionMessage('Voice logs cleared successfully.');
        setTimeout(() => setActionMessage(''), 3000);
      }
    } catch (e) {
      console.error('Failed to clear voice logs:', e);
    }
  }

  // Periodic 5s polling for voice logs to guarantee live feed
  useEffect(() => {
    const timer = setInterval(() => {
      fetchVoiceLogs();
    }, 5000);
    return () => clearInterval(timer);
  }, [fetchVoiceLogs]);

  // Summary counters from queueData
  const allTokens = queueData?.tokens || [];
  const waitingTokens = allTokens.filter((t) => t.status === 'waiting');
  const inConsultCount = inConsult ? 1 : allTokens.filter((t) => t.status === 'in_consult').length;
  const doneTodayCount = allTokens.filter((t) => t.status === 'done').length;
  const cancelledCount = allTokens.filter((t) => t.status === 'cancelled').length;

  // Credit calculation
  const callsUsed = usage ? usage.real_calls_today : 0;
  const maxCalls = usage ? usage.limit : 150;
  const reserve = usage ? (usage.reserve ?? 40) : 40;
  const usageRatio = maxCalls > 0 ? callsUsed / maxCalls : 0;
  const isLimitReached = usageRatio >= 1.0;
  const isAmber = usageRatio >= 0.8 && !isLimitReached;

  return (
    <div className={`dashboard-container ${isPresentMode ? 'presentation-mode' : ''}`}>
      {/* Paused Credit Limit Banner */}
      {isLimitReached && (
        <div className="limit-paused-banner">
          ⚠️ Voice is paused to save credits. Typing still works.
        </div>
      )}

      {/* 1. Dashboard Header */}
      <header className="dashboard-header">
        <div className="header-left">
          <h1 className="dash-clinic-title">Demo Clinic — Live Queue Dashboard</h1>
          <div className="dash-header-subrow">
            <div className="dash-tabs" role="tablist" aria-label="Queue day selector">
              <button
                type="button"
                role="tab"
                aria-selected={dayTab === 'today'}
                className={`dash-tab ${dayTab === 'today' ? 'active' : ''}`}
                onClick={() => setDayTab('today')}
              >
                Today
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={dayTab === 'tomorrow'}
                className={`dash-tab ${dayTab === 'tomorrow' ? 'active' : ''}`}
                onClick={() => setDayTab('tomorrow')}
              >
                Tomorrow
              </button>
            </div>

            {/* P2-5: Live status dot driven by WebSocket & last updated timestamp */}
            <div className="dash-live-status-badge">
              <span className={`live-dot ${wsStatus}`} />
              <span className="live-status-text">{wsStatus === 'live' ? 'Live' : 'Reconnecting'}</span>
              <span className="live-status-divider">·</span>
              <span className="live-updated-time">Last updated: {lastUpdated}</span>
            </div>
          </div>
        </div>

        <div className="header-right">
          {/* Phase 7: Credits Meter Badge (Hidden in presentation mode and clean recording mode) */}
          {!isPresentMode && !isClean && (
            <div className="credits-badge-slot">
              <div
                className={`calls-meter-badge ${
                  isLimitReached ? 'meter-red' : isAmber ? 'meter-amber' : 'meter-green'
                }`}
              >
                Gnani calls: {callsUsed}/{maxCalls} (Reserve: {reserve})
              </div>
              {usage?.estimated_credits_used !== null && usage?.estimated_credits_used !== undefined && (
                <span className="credits-estimated-pill">
                  ~{usage.estimated_credits_used} cr
                </span>
              )}
            </div>
          )}

          <button
            type="button"
            className="patient-view-btn"
            onClick={() => {
              window.history.pushState({}, '', '/');
              window.dispatchEvent(new PopStateEvent('popstate'));
            }}
          >
            ← Patient Voice App
          </button>
          {!isPresentMode && !isClean && (
            <>
              <button
                type="button"
                className="tests-view-btn"
                onClick={() => {
                  window.history.pushState({}, '', '/tests');
                  window.dispatchEvent(new PopStateEvent('popstate'));
                }}
              >
                🧪 Tests
              </button>
              <button
                type="button"
                className="about-view-btn"
                onClick={() => {
                  window.history.pushState({}, '', '/about');
                  window.dispatchEvent(new PopStateEvent('popstate'));
                }}
              >
                ℹ️ About
              </button>
            </>
          )}
        </div>
      </header>

      {/* P2-5: Summary Counters (Waiting, In Consultation, Done Today, Cancelled) */}
      <section className="summary-counters-section" aria-label="Queue Summary Counters">
        <div className="counter-card counter-waiting">
          <span className="counter-val">{waitingTokens.length}</span>
          <span className="counter-lbl">Waiting</span>
        </div>
        <div className="counter-card counter-consult">
          <span className="counter-val">{inConsultCount}</span>
          <span className="counter-lbl">In Consultation</span>
        </div>
        <div className="counter-card counter-done">
          <span className="counter-val">{doneTodayCount}</span>
          <span className="counter-lbl">Done Today</span>
        </div>
        <div className="counter-card counter-cancelled">
          <span className="counter-val">{cancelledCount}</span>
          <span className="counter-lbl">Cancelled</span>
        </div>
      </section>

      {/* Global Action Bar */}
      <section className="action-bar" aria-label="Dashboard actions">
        <div className="action-buttons-group">
          <button type="button" className="action-btn btn-call-next" onClick={handleCallNext}>
            📢 Call Next Patient
          </button>
          {!isPresentMode && !isClean && (
            <>
              <button type="button" className="action-btn btn-seed" onClick={handleSeedDemo}>
                🌱 Seed Demo Data (1-6)
              </button>
              <button type="button" className="action-btn btn-reset" onClick={handleResetDemo}>
                🔄 Reset Demo
              </button>
            </>
          )}
        </div>

        {/* P2-5: Keyboard shortcuts hint line */}
        <div className="keyboard-shortcuts-hint">
          Shortcuts: Press <strong>N</strong> for Call next · <strong>D</strong> for Mark done
        </div>

        {actionMessage && <div className="action-toast">{actionMessage}</div>}
      </section>

      {/* 2-Column Main Layout */}
      <main className="dashboard-grid">
        {/* LEFT COLUMN: In Consult & Waiting Queue */}
        <section className="col-left">
          {/* Now In Consultation Card */}
          <div className="dash-card consult-card">
            <h2 className="card-section-title">🩺 Now in Consultation</h2>
            {inConsult ? (
              <div className="in-consult-content">
                <div className="consult-token-badge">
                  <span className="tok-label">TOKEN</span>
                  <span className="tok-huge">#{inConsult.number}</span>
                </div>
                <div className="consult-details">
                  <p className="patient-label">{inConsult.label}</p>
                  <p className="patient-lang">Language: <strong>{formatLanguageName(inConsult.language)}</strong></p>
                  <p className="patient-status">Status: <span className="status-badge-consult">IN CONSULT</span></p>
                </div>
                <div className="consult-actions">
                  <button
                    type="button"
                    className="consult-btn btn-mark-done"
                    onClick={() => handleMarkDone(inConsult.id)}
                  >
                    ✓ Mark Done (D)
                  </button>
                  <button
                    type="button"
                    className="consult-btn btn-no-show"
                    onClick={() => handleMarkNoShow(inConsult.id)}
                  >
                    ✕ No-Show
                  </button>
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <p>No patient currently in consultation.</p>
                <button type="button" className="empty-call-btn" onClick={handleCallNext}>
                  Click "Call Next Patient" to start
                </button>
              </div>
            )}
          </div>

          {/* Waiting Queue List */}
          <div className="dash-card waiting-card">
            <div className="waiting-card-header">
              <h2 className="card-section-title">⏳ Waiting Patients</h2>
              <span className="waiting-count-pill">{waitingTokens.length} waiting</span>
            </div>

            {waitingTokens.length > 0 ? (
              <div className="waiting-list">
                {waitingTokens.map((t, idx) => (
                  <div
                    key={t.id}
                    className={`waiting-row ${highlightedTokenId === t.id ? 'highlight-pulse' : ''}`}
                  >
                    <div className="row-left">
                      <span className="row-token-num">Position {idx + 1} - Token {t.number}</span>
                      <span className="row-patient-label">{t.label}</span>
                    </div>
                    <div className="row-right">
                      <span className="lang-tag">{formatLanguageName(t.language)}</span>
                      <span className="waiting-tag">Waiting</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <p>No patients waiting.</p>
              </div>
            )}
          </div>
        </section>

        {/* RIGHT COLUMN: Voice Activity Feed */}
        <section className="col-right">
          <div className="dash-card activity-card">
            <div className="activity-card-header">
              <div className="activity-header-left">
                <h2 className="card-section-title">🎙 Voice Activity Feed</h2>
                <span className="activity-count-pill">{voiceLogs.length} events</span>
              </div>
              {!isClean && (
                <button
                  type="button"
                  className="btn-clear-logs"
                  onClick={handleClearVoiceLogs}
                  disabled={voiceLogs.length === 0}
                  title="Clear all recorded voice logs"
                >
                  Clear voice log
                </button>
              )}
            </div>

            {voiceLogs.length > 0 ? (
              <div className="activity-feed">
                {voiceLogs.map((log) => (
                  <div key={log.id} className="activity-item">
                    <div className="activity-meta">
                      <span className="activity-time">{log.time}</span>
                      <span className={`intent-badge intent-${(log.intent || '').toLowerCase()}`}>
                        {log.intent}
                      </span>
                      {log.token_number && (
                        <span className="activity-tok-num">Token #{log.token_number}</span>
                      )}
                      <span className="activity-lang">{formatLanguageName(log.detected_language)}</span>
                      {(!log.ok || log.error) && (
                        <span className="activity-error-badge" title={log.error || 'Failed'}>
                          {(log.error || 'Failed').replace(/_/g, ' ')}
                        </span>
                      )}
                    </div>
                    <p className="activity-transcript">
                      "{log.transcript || 'Speech processed'}"
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <p>No voice activity yet.</p>
                <p className="empty-hint">Spoken turns from the patient app appear here live.</p>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
