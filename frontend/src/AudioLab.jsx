import React, { useState, useEffect } from 'react';
import './AudioLab.css';
import { API_BASE } from './config.js';

export default function AudioLab({ onBack }) {
  const isDev = window.location.search.includes('dev=1');

  // Switch: Send raw audio (no cleaning)
  const [sendRawAudio, setSendRawAudio] = useState(() => {
    try {
      return localStorage.getItem('vq_send_raw_audio') === 'true';
    } catch (e) {
      return false;
    }
  });

  // Last 10 turns state
  const [turns, setTurns] = useState([]);
  const [loadingTurns, setLoadingTurns] = useState(false);
  const [turnsError, setTurnsError] = useState(null);

  // Manual comparison form state
  const [sentence, setSentence] = useState('');
  const [cleanedTranscript, setCleanedTranscript] = useState('');
  const [rawTranscript, setRawTranscript] = useState('');
  const [whichBetter, setWhichBetter] = useState('cleaned');
  const [notes, setNotes] = useState('');
  const [savingCompare, setSavingCompare] = useState(false);
  const [compareSuccess, setCompareSuccess] = useState(null);

  // Comparisons table state
  const [comparisons, setComparisons] = useState([]);
  const [loadingComparisons, setLoadingComparisons] = useState(false);

  // Debug audio saving warning & clear state
  const [debugSaveAudio, setDebugSaveAudio] = useState(false);
  const [clearingAudio, setClearingAudio] = useState(false);
  const [clearAudioMsg, setClearAudioMsg] = useState(null);

  useEffect(() => {
    if (isDev) {
      loadTurns();
      loadComparisons();
      fetchHealth();
    }
  }, [isDev]);

  async function fetchHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        const data = await res.json();
        setDebugSaveAudio(Boolean(data.debug_save_audio));
      }
    } catch (e) {}
  }

  async function handleDeleteAllDebugAudio() {
    if (!window.confirm('Are you sure you want to delete all saved debug audio clips?')) {
      return;
    }
    setClearingAudio(true);
    setClearAudioMsg(null);
    try {
      const res = await fetch(`${API_BASE}/debug-audio/clear`, { method: 'POST' });
      if (res.ok) {
        setClearAudioMsg('All debug audio clips deleted successfully.');
        loadTurns();
        setTimeout(() => setClearAudioMsg(null), 3500);
      }
    } catch (err) {
      console.warn('Failed to clear debug audio:', err);
    } finally {
      setClearingAudio(false);
    }
  }

  function handleRawAudioToggle(val) {
    setSendRawAudio(val);
    try {
      localStorage.setItem('vq_send_raw_audio', val ? 'true' : 'false');
    } catch (e) {}
  }

  async function loadTurns() {
    setLoadingTurns(true);
    setTurnsError(null);
    try {
      const res = await fetch(`${API_BASE}/audio-lab/turns`);
      if (res.ok) {
        const data = await res.json();
        setTurns(data);
      } else {
        setTurnsError('Failed to load recent voice turns.');
      }
    } catch (err) {
      setTurnsError('Network error connecting to backend.');
    } finally {
      setLoadingTurns(false);
    }
  }

  async function loadComparisons() {
    setLoadingComparisons(true);
    try {
      const res = await fetch(`${API_BASE}/audio-compare`);
      if (res.ok) {
        const data = await res.json();
        setComparisons(data);
      }
    } catch (err) {
      console.warn('Failed to load comparisons:', err);
    } finally {
      setLoadingComparisons(false);
    }
  }

  async function handleSaveComparison(e) {
    e.preventDefault();
    if (!sentence.trim()) return;

    setSavingCompare(true);
    setCompareSuccess(null);
    try {
      const res = await fetch(`${API_BASE}/audio-compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sentence: sentence.trim(),
          cleaned_transcript: cleanedTranscript.trim(),
          raw_transcript: rawTranscript.trim(),
          which_better: whichBetter,
          notes: notes.trim(),
        }),
      });

      if (res.ok) {
        setCompareSuccess('Comparison saved to table audio_compare!');
        setSentence('');
        setCleanedTranscript('');
        setRawTranscript('');
        setNotes('');
        loadComparisons();
        setTimeout(() => setCompareSuccess(null), 3000);
      }
    } catch (err) {
      console.warn('Failed to save comparison:', err);
    } finally {
      setSavingCompare(false);
    }
  }

  if (!isDev) {
    return (
      <div className="audio-lab-page">
        <div className="audio-lab-container restricted-card">
          <h2>🔒 Access Restricted</h2>
          <p>
            The Audio Lab developer page is only reachable with <code>?dev=1</code> in the URL.
          </p>
          <a href="/audio-lab?dev=1" className="lab-btn primary-btn">
            Access with ?dev=1
          </a>
          <button type="button" className="lab-btn secondary-btn" onClick={onBack}>
            ← Back to Patient Page
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="audio-lab-page">
      <div className="audio-lab-container">
        {/* Header */}
        <header className="audio-lab-header">
          <div className="header-left">
            <button type="button" className="back-link-btn" onClick={onBack}>
              ← Back to App
            </button>
            <h1>🔬 Audio Lab & Quality Tools</h1>
          </div>
          <span className="dev-mode-pill">DEV MODE (?dev=1)</span>
        </header>

        {/* Switch Card: Send raw audio (no cleaning) */}
        <section className="lab-card switch-card">
          <div className="switch-row">
            <div className="switch-info">
              <h3>Send raw audio (no cleaning)</h3>
              <p>
                When enabled, sets per-request flag <code>clean=false</code> on <code>/voice/turn</code>,
                allowing you to test the exact same sentence with and without server ffmpeg filters.
              </p>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={sendRawAudio}
                onChange={(e) => handleRawAudioToggle(e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
          <div className="switch-status-note">
            Current flag sent with voice turns: <strong>{sendRawAudio ? 'clean=false (Raw)' : 'clean=true (Cleaned)'}</strong>
          </div>
        </section>

        {/* Section 1: Last 10 Voice Turns */}
        <section className="lab-card">
          {debugSaveAudio && (
            <div
              className="lab-alert warning"
              style={{
                backgroundColor: '#FEF3C7',
                color: '#92400E',
                border: '1.5px solid #C8893B',
                padding: '12px 16px',
                borderRadius: '8px',
                marginBottom: '16px',
                fontWeight: 600,
              }}
            >
              ⚠️ Warning: Debug audio saving is currently ON in backend/.env. Saved clips may contain real patient voices.
            </div>
          )}

          {clearAudioMsg && (
            <div className="lab-alert success" style={{ marginBottom: '16px' }}>
              {clearAudioMsg}
            </div>
          )}

          <div className="card-header-row">
            <div>
              <h2>Last 10 Voice Turns</h2>
              <p className="card-subtext">
                Live telemetry from <code>voice_logs</code>. Raw and cleaned playback requires{' '}
                <code>DEBUG_SAVE_AUDIO=true</code> in <code>backend/.env</code>.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button
                type="button"
                className="refresh-btn"
                onClick={loadTurns}
                disabled={loadingTurns}
              >
                {loadingTurns ? 'Refreshing...' : '🔄 Refresh Turns'}
              </button>
              <button
                type="button"
                className="delete-debug-audio-btn"
                onClick={handleDeleteAllDebugAudio}
                disabled={clearingAudio}
                style={{
                  backgroundColor: '#FDF2F0',
                  color: '#9E2A2B',
                  border: '1.5px solid #9E2A2B',
                  padding: '8px 14px',
                  borderRadius: '10px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {clearingAudio ? 'Deleting...' : '🗑️ Delete all debug audio'}
              </button>
            </div>
          </div>

          {turnsError && <div className="lab-alert error">{turnsError}</div>}

          <div className="turns-table-wrapper">
            <table className="lab-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Transcript</th>
                  <th>Lang</th>
                  <th>Duration</th>
                  <th>Peak</th>
                  <th>RMS</th>
                  <th>Cleaned?</th>
                  <th>Raw Audio</th>
                  <th>Cleaned Audio</th>
                </tr>
              </thead>
              <tbody>
                {turns.length === 0 ? (
                  <tr>
                    <td colSpan="9" className="empty-cell">
                      {loadingTurns ? 'Loading turns...' : 'No voice turns logged yet. Speak into the mic on the patient page to populate.'}
                    </td>
                  </tr>
                ) : (
                  turns.map((t) => (
                    <tr key={t.id}>
                      <td className="time-col">{t.created_at}</td>
                      <td className="transcript-col">
                        {t.transcript || '—'}
                        {t.error && (
                          <div style={{ color: '#C84B31', fontSize: '0.75rem', marginTop: '4px', wordBreak: 'break-word' }}>
                            ⚠️ {t.error}
                          </div>
                        )}
                      </td>
                      <td><code>{t.detected_language}</code></td>
                      <td>{t.duration !== null ? `${t.duration}s` : '—'}</td>
                      <td>{t.peak !== null ? t.peak : '—'}</td>
                      <td>{t.rms !== null ? t.rms : '—'}</td>
                      <td>
                        <span className={`cleaned-badge ${t.cleaned ? 'yes' : 'no'}`}>
                          {t.cleaned ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td>
                        {t.raw_audio_url ? (
                          <audio controls className="mini-audio" src={`${API_BASE}${t.raw_audio_url}`} />
                        ) : (
                          <span className="no-audio-text">No clip</span>
                        )}
                      </td>
                      <td>
                        {t.cleaned_audio_url ? (
                          <audio controls className="mini-audio" src={`${API_BASE}${t.cleaned_audio_url}`} />
                        ) : (
                          <span className="no-audio-text">No clip</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Section 2: Manual Audio Comparison & CSV Export */}
        <section className="lab-card">
          <div className="card-header-row">
            <div>
              <h2>Manual Audio Comparison (table <code>audio_compare</code>)</h2>
              <p className="card-subtext">
                Record the same spoken phrase with and without cleaning, compare Prisma's transcripts,
                and log which performed better.
              </p>
            </div>
            <a
              href={`${API_BASE}/audio-compare/export.csv`}
              className="export-btn"
              download="audio_compare.csv"
            >
              📥 Export CSV
            </a>
          </div>

          {compareSuccess && <div className="lab-alert success">{compareSuccess}</div>}

          {/* Form */}
          <form className="compare-form" onSubmit={handleSaveComparison}>
            <div className="form-grid">
              <div className="form-group full-width">
                <label>Spoken Sentence (Reference)</label>
                <input
                  type="text"
                  placeholder="e.g. Naaku repu token kavali"
                  value={sentence}
                  onChange={(e) => setSentence(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Cleaned Audio Transcript</label>
                <input
                  type="text"
                  placeholder="Transcript returned with clean=true"
                  value={cleanedTranscript}
                  onChange={(e) => setCleanedTranscript(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Raw Audio Transcript</label>
                <input
                  type="text"
                  placeholder="Transcript returned with clean=false"
                  value={rawTranscript}
                  onChange={(e) => setRawTranscript(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Which Was Better?</label>
                <select
                  value={whichBetter}
                  onChange={(e) => setWhichBetter(e.target.value)}
                >
                  <option value="cleaned">Cleaned audio was better</option>
                  <option value="raw">Raw audio was better</option>
                  <option value="same">Both were identical / equally good</option>
                  <option value="failed">Both failed or inaccurate</option>
                </select>
              </div>

              <div className="form-group">
                <label>Notes / Acoustic Environment</label>
                <input
                  type="text"
                  placeholder="e.g. Ceiling fan running on high, quiet room"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>
            </div>

            <div className="form-actions">
              <button
                type="submit"
                className="lab-btn primary-btn"
                disabled={savingCompare || !sentence.trim()}
              >
                {savingCompare ? 'Saving...' : '💾 Save Comparison'}
              </button>
            </div>
          </form>

          {/* Saved Comparisons Table */}
          <div className="saved-comparisons-table-wrapper">
            <h3>Saved Comparisons ({comparisons.length})</h3>
            <table className="lab-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Spoken Sentence</th>
                  <th>Cleaned Transcript</th>
                  <th>Raw Transcript</th>
                  <th>Which Better</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {comparisons.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="empty-cell">
                      {loadingComparisons ? 'Loading comparisons...' : 'No manual comparisons saved yet.'}
                    </td>
                  </tr>
                ) : (
                  comparisons.map((c) => (
                    <tr key={c.id}>
                      <td>{c.id}</td>
                      <td><strong>{c.sentence}</strong></td>
                      <td>{c.cleaned_transcript || '—'}</td>
                      <td>{c.raw_transcript || '—'}</td>
                      <td>
                        <span className={`better-pill ${c.which_better}`}>
                          {c.which_better}
                        </span>
                      </td>
                      <td className="notes-cell">{c.notes || '—'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}

