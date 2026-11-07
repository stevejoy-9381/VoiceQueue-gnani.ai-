import React, { useState, useEffect, useCallback } from 'react';
import './VoiceTests.css';
import { API_BASE } from './config.js';
import { formatTimeIST } from './timeUtils.js';

const INTENTS = ['BOOK', 'STATUS', 'CANCEL', 'YES', 'NO', 'UNKNOWN'];
const NOISE_LEVELS = [
  { value: 'quiet', label: 'Quiet Room' },
  { value: 'fan', label: 'Fan / AC Noise' },
  { value: 'street', label: 'Street / Traffic Noise' },
];
const LANGUAGES = [
  { value: 'te', label: 'Telugu (తెలుగు)' },
  { value: 'en', label: 'English' },
  { value: 'mix', label: 'Mix (Telugu + English)' },
];

export default function VoiceTests({ onBack }) {
  // Form fields
  const [language, setLanguage] = useState('te');
  const [noise, setNoise] = useState('quiet');
  const [expectedIntent, setExpectedIntent] = useState('BOOK');
  const [gotIntent, setGotIntent] = useState('BOOK');
  const [passed, setPassed] = useState(null);
  const [intendedSentence, setIntendedSentence] = useState('');
  const [transcript, setTranscript] = useState('');
  const [note, setNote] = useState('');

  // Status and feedback
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState('');

  // Data lists
  const [tests, setTests] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  const handleExpectedChange = (val) => {
    setExpectedIntent(val);
  };

  const handleGotChange = (val) => {
    setGotIntent(val);
  };

  // Fetch telemetry data
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [testsRes, summaryRes] = await Promise.all([
        fetch(`${API_BASE}/voice-tests`),
        fetch(`${API_BASE}/voice-tests/summary`),
      ]);

      if (testsRes.ok) {
        const testsData = await testsRes.json();
        setTests(testsData);
      }
      if (summaryRes.ok) {
        const summaryData = await summaryRes.json();
        setSummary(summaryData);
      }
    } catch (err) {
      console.error('Failed to load voice test telemetry:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle form submission
  async function handleSubmit(e) {
    e.preventDefault();
    if (!transcript.trim()) {
      setFeedback('⚠️ Please enter a transcript for the test trial.');
      return;
    }
    if (passed === null) {
      setFeedback('⚠️ Please select a trial outcome (PASS or FAIL).');
      return;
    }

    setSubmitting(true);
    setFeedback('');

    try {
      const payload = {
        language,
        noise,
        expected_intent: expectedIntent,
        got_intent: gotIntent,
        intended_sentence: intendedSentence.trim() || null,
        transcript: transcript.trim(),
        passed,
        note: note.trim() || null,
      };

      const res = await fetch(`${API_BASE}/voice-tests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      setFeedback('✅ Voice test trial recorded successfully!');
      setIntendedSentence('');
      setTranscript('');
      setPassed(null);
      setNote('');
      fetchData();
    } catch (err) {
      setFeedback('❌ Failed to save voice test. Please try again.');
    } finally {
      setSubmitting(false);
      setTimeout(() => setFeedback(''), 4000);
    }
  }

  // Handle CSV Export
  function handleExportCsv() {
    window.location.href = `${API_BASE}/voice-tests/export`;
  }

  // Compute Language x Noise Grid stats
  const gridLangs = [
    { key: 'te', label: 'Telugu' },
    { key: 'en', label: 'English' },
    { key: 'mix', label: 'Mix' },
  ];
  const gridNoises = [
    { key: 'quiet', label: 'Quiet' },
    { key: 'fan', label: 'Fan / AC' },
    { key: 'street', label: 'Street' },
  ];

  const breakdownMap = {};
  if (summary && summary.breakdown) {
    summary.breakdown.forEach((item) => {
      breakdownMap[`${item.language}_${item.noise}`] = item;
    });
  }

  const hasTrials = summary && summary.total_trials > 0;

  return (
    <div className="tests-container">
      {/* 1. Header */}
      <header className="tests-header">
        <div className="tests-header-left">
          <h1 className="tests-title">VoiceQueue — Voice Testing & Telemetry</h1>
          <p className="tests-subtitle">
            Manual trial logging and empirical accuracy metrics across background noise conditions
          </p>
        </div>
        <div className="tests-header-right">
          <button type="button" className="btn-export-csv" onClick={handleExportCsv}>
            Export CSV
          </button>
          <button type="button" className="btn-back-dash" onClick={onBack}>
            ← Back to Dashboard
          </button>
        </div>
      </header>

      {/* Feedback Alert */}
      {feedback && <div className="tests-feedback-banner">{feedback}</div>}

      <div className="tests-grid">
        {/* 2. Left Column: Form to log test trial */}
        <section className="tests-form-card">
          <h2 className="section-title">Log Voice Test Trial</h2>
          <form onSubmit={handleSubmit} className="voice-test-form">
            <div className="form-row-2">
              <div className="form-group">
                <label htmlFor="test-lang">Language</label>
                <select
                  id="test-lang"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  {LANGUAGES.map((l) => (
                    <option key={l.value} value={l.value}>
                      {l.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="test-noise">Noise Environment</label>
                <select
                  id="test-noise"
                  value={noise}
                  onChange={(e) => setNoise(e.target.value)}
                >
                  {NOISE_LEVELS.map((n) => (
                    <option key={n.value} value={n.value}>
                      {n.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-row-2">
              <div className="form-group">
                <label htmlFor="test-exp">Expected Intent</label>
                <select
                  id="test-exp"
                  value={expectedIntent}
                  onChange={(e) => handleExpectedChange(e.target.value)}
                >
                  {INTENTS.map((i) => (
                    <option key={i} value={i}>
                      {i}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="test-got">Got Intent</label>
                <select
                  id="test-got"
                  value={gotIntent}
                  onChange={(e) => handleGotChange(e.target.value)}
                >
                  {INTENTS.map((i) => (
                    <option key={i} value={i}>
                      {i}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="test-intended">Sentence I meant to say</label>
              <input
                type="text"
                id="test-intended"
                value={intendedSentence}
                onChange={(e) => setIntendedSentence(e.target.value)}
                placeholder="e.g. I need a token for tomorrow / repu naaku token kavali"
              />
            </div>

            <div className="form-group">
              <label htmlFor="test-transcript">Recognized Transcript</label>
              <textarea
                id="test-transcript"
                rows="3"
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
                placeholder="e.g. I need a token for tomorrow / repu naaku token kavali"
                required
              />
            </div>

            <div className="form-group">
              <label>Trial Outcome</label>
              <div className="pass-fail-toggle">
                <button
                  type="button"
                  className={`toggle-btn ${passed === true ? 'active pass' : ''}`}
                  onClick={() => setPassed(true)}
                >
                  ✓ PASS
                </button>
                <button
                  type="button"
                  className={`toggle-btn ${passed === false ? 'active fail' : ''}`}
                  onClick={() => setPassed(false)}
                >
                  ✕ FAIL
                </button>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="test-note">Notes / Observations (Optional)</label>
              <input
                type="text"
                id="test-note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="e.g. Spoke 1 meter from phone, ceiling fan was at level 4"
              />
            </div>

            <button type="submit" className="btn-submit-test" disabled={submitting}>
              {submitting ? 'Saving Trial...' : 'Save Voice Test Row'}
            </button>
          </form>
        </section>

        {/* 3. Right Column: Language x Noise Grid Summary Table */}
        <section className="tests-summary-card">
          <div className="summary-header">
            <h2 className="section-title">Language x Noise Grid Summary</h2>
            <span className="overall-stat-pill">
              Overall: {hasTrials ? `${summary.overall_pass_rate}% (${summary.total_passed}/${summary.total_trials})` : '-'}
            </span>
          </div>

          {!hasTrials ? (
            <div className="empty-summary-box">
              <p>No voice test trials logged yet.</p>
              <span className="empty-hint">
                Perform a voice test using hold-to-talk in different noise settings, then record the result here.
              </span>
            </div>
          ) : (
            <div className="summary-table-wrapper">
              <table className="summary-table grid-table">
                <thead>
                  <tr>
                    <th>Language</th>
                    {gridNoises.map((n) => (
                      <th key={n.key}>{n.label}</th>
                    ))}
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {gridLangs.map((l) => {
                    let langTotal = 0;
                    let langPassed = 0;
                    return (
                      <tr key={l.key}>
                        <td className="cell-lang">{l.label}</td>
                        {gridNoises.map((n) => {
                          const item = breakdownMap[`${l.key}_${n.key}`];
                          if (item && item.total > 0) {
                            langTotal += item.total;
                            langPassed += item.passed;
                            return (
                              <td key={n.key}>
                                <span
                                  className={`rate-pill ${
                                    item.pass_rate >= 90
                                      ? 'rate-green'
                                      : item.pass_rate >= 70
                                      ? 'rate-amber'
                                      : 'rate-red'
                                  }`}
                                >
                                  {item.passed}/{item.total} ({item.pass_rate}%)
                                </span>
                              </td>
                            );
                          }
                          return <td key={n.key} className="cell-empty">-</td>;
                        })}
                        <td className="cell-total">
                          {langTotal > 0 ? (
                            <strong>
                              {langPassed}/{langTotal} ({Math.round((langPassed / langTotal) * 100)}%)
                            </strong>
                          ) : (
                            '-'
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      {/* 4. Bottom Section: All Test Records */}
      <section className="tests-history-card">
        <div className="history-header">
          <h2 className="section-title">Voice Test Log History</h2>
          <span className="history-count">{tests.length} trials recorded</span>
        </div>

        {tests.length === 0 ? (
          <div className="empty-history-box">No test trials recorded yet.</div>
        ) : (
          <div className="history-table-wrapper">
            <table className="history-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Outcome</th>
                  <th>Language</th>
                  <th>Noise</th>
                  <th>Expected</th>
                  <th>Got</th>
                  <th>Sentence Meant</th>
                  <th>Transcript</th>
                  <th>Note</th>
                  <th>Logged At</th>
                </tr>
              </thead>
              <tbody>
                {tests.map((t) => (
                  <tr key={t.id}>
                    <td>{t.id}</td>
                    <td>
                      <span className={`status-tag ${t.passed ? 'tag-pass' : 'tag-fail'}`}>
                        {t.passed ? 'PASS' : 'FAIL'}
                      </span>
                    </td>
                    <td>
                      <span className="lang-tag">
                        {t.language === 'te' ? 'TE' : t.language === 'en' ? 'EN' : 'MIX'}
                      </span>
                    </td>
                    <td className="cell-noise">{t.noise}</td>
                    <td><code>{t.expected_intent}</code></td>
                    <td><code>{t.got_intent}</code></td>
                    <td className="cell-sentence-meant">{t.intended_sentence || '—'}</td>
                    <td className="cell-transcript">"{t.transcript}"</td>
                    <td className="cell-note">{t.note || '—'}</td>
                    <td className="cell-time">
                      {formatTimeIST(t.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
