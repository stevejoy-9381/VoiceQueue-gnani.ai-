import React, { useState, useEffect } from 'react';
import './AboutPage.css';
import { API_BASE } from './config.js';

export default function AboutPage({ onNavigate }) {
  const [groqConfigured, setGroqConfigured] = useState(false);
  const [teluguReviewed, setTeluguReviewed] = useState(false);
  const [voiceTestsSummary, setVoiceTestsSummary] = useState(null);
  const [textTestResults, setTextTestResults] = useState(null);

  useEffect(() => {
    // Check if Groq and Telugu review are configured
    fetch(`${API_BASE}/health`)
      .then((res) => (res.ok ? res.json() : {}))
      .then((data) => {
        setGroqConfigured(Boolean(data.groq_configured));
        setTeluguReviewed(Boolean(data.telugu_reviewed));
      })
      .catch(() => {});

    // Also check dedicated /telugu-review-status endpoint as fallback
    fetch(`${API_BASE}/telugu-review-status`)
      .then((res) => (res.ok ? res.json() : {}))
      .then((data) => {
        if (data.reviewed_by_native_speaker || data.all_reviewed) {
          setTeluguReviewed(true);
        }
      })
      .catch(() => {});

    // Fetch real voice tests summary
    fetch(`${API_BASE}/voice-tests/summary`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        setVoiceTestsSummary(data);
      })
      .catch(() => {});

    // Fetch text-only intent test results (never hardcoded)
    fetch(`${API_BASE}/voice-tests/text-summary`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.total) {
          setTextTestResults(data);
        }
      })
      .catch(() => {});
  }, []);

  // Build 3x3 Language x Noise grid data
  const languages = [
    { key: 'te', label: 'Telugu' },
    { key: 'en', label: 'English' },
    { key: 'mix', label: 'Mix' },
  ];
  const noiseLevels = [
    { key: 'quiet', label: 'Quiet' },
    { key: 'fan', label: 'Fan / AC' },
    { key: 'street', label: 'Street' },
  ];

  const gridMap = {};
  if (voiceTestsSummary && voiceTestsSummary.breakdown) {
    voiceTestsSummary.breakdown.forEach((item) => {
      gridMap[`${item.language}_${item.noise}`] = `${item.passed}/${item.total}`;
    });
  }

  const hasVoiceTests =
    voiceTestsSummary &&
    voiceTestsSummary.total_trials !== undefined &&
    voiceTestsSummary.total_trials > 0;

  return (
    <div className="about-viewport">
      <header className="about-header">
        <div className="about-header-content">
          <h1 className="about-title">About VoiceQueue</h1>
          <p className="about-tagline">
            Voice-First Clinic Token & Queue Management System for Demo Clinic
          </p>
          {teluguReviewed && (
            <p className="telugu-reviewed-line" data-testid="telugu-reviewed-line">
              ✓ Reviewed by a native speaker
            </p>
          )}
        </div>
        <div className="about-nav-buttons">
          <button
            type="button"
            className="nav-btn primary"
            onClick={() => onNavigate('/')}
          >
            🎙️ Patient Voice App
          </button>
          <button
            type="button"
            className="nav-btn secondary"
            onClick={() => onNavigate('/clinic')}
          >
            📋 Clinic Dashboard
          </button>
          <button
            type="button"
            className="nav-btn outline"
            onClick={() => onNavigate('/tests')}
          >
            🧪 Test Telemetry
          </button>
        </div>
      </header>

      <main className="about-content">
        {/* Synthetic Notice Banner */}
        <section className="notice-banner">
          <span className="notice-icon">ℹ️</span>
          <p className="notice-text">
            <strong>All data in this demo is synthetic.</strong> No real patient names, doctor records,
            or protected health information (PHI) are stored.
          </p>
        </section>

        {/* 1. What VoiceQueue is */}
        <section className="about-card">
          <h2 className="card-heading">What is VoiceQueue?</h2>
          <p>
            A demo for small clinics. Not connected to a real clinic. Patients can book clinic tokens, check their live position in queue,
            and cancel appointments by speaking in <strong>Telugu</strong>, <strong>English</strong>, or <strong>Mix (Telugu + English)</strong>.
          </p>
          <p>
            The system combines hold-to-talk mobile audio capture, instant speech-to-text, bilingual intent routing,
            spelling out all token numbers phonetically as words, and playing spoken audio replies.
          </p>
        </section>

        {/* 2. Models Used */}
        <section className="about-card">
          <h2 className="card-heading">Models & Speech Stack</h2>
          <div className="models-grid">
            <div className="model-box">
              <span className="model-badge">Speech-to-Text (STT)</span>
              <h3>Prisma (STT, prisma-v3.0)</h3>
              <p>Gnani Prisma (prisma-v3.0) converts patient speech into text.</p>
            </div>

            <div className="model-box">
              <span className="model-badge">Text-to-Speech (TTS)</span>
              <h3>Timbre v2.5 (TTS)</h3>
              <p>Gnani Timbre v2.5 synthesizes spoken replies using Lavanya for Telugu and Trupti for English.</p>
            </div>

            {groqConfigured && (
              <div className="model-box">
                <span className="model-badge">Optional NLU Fallback</span>
                <h3>Groq (Llama-3.1-8B-Instant)</h3>
                <p>Transcript text is sent to Groq only when the rules fail.</p>
              </div>
            )}
          </div>
        </section>

        {/* 3. System Limits & Scope */}
        <section className="about-card">
          <h2 className="card-heading">System Limits & Scope</h2>
          <ul className="limitations-list">
            <li>
              <strong>Demo uses synthetic data only:</strong> All patient tokens and consultations use simulated clinic data.
            </li>
            <li>
              <strong>Rule-based intent (Gnani has no chat model):</strong> Routing uses deterministic rule parsing because Gnani provides STT/TTS without a conversational LLM.
            </li>
            <li>
              <strong>One clinic:</strong> Scoped strictly to single-clinic outpatient token queues.
            </li>
            <li>
              <strong>No real phone data:</strong> No real phone numbers or personal identifiers are collected, stored, or required.
            </li>
          </ul>
        </section>

        {/* 4. Test Results */}
        <section className="about-card highlight-card">
          <h2 className="card-heading">Test Results</h2>
          
          {/* (a) Text-only intent test (no audio) */}
          <div className="test-block">
            <h3 className="test-block-title">Text-only intent test</h3>
            <p className="test-block-desc">
              Written phrases are run through the intent rules without audio.
            </p>
            <div className="test-stat-row">
              <span className="test-stat-badge">
                {textTestResults
                  ? `Text-only intent test: ${textTestResults.passed} of ${textTestResults.total} passed (no audio)`
                  : 'Text-only intent test: loading... (no audio)'}
              </span>
            </div>
          </div>

          <hr className="test-divider" />

          {/* (b) Real voice results */}
          <div className="test-block">
            <h3 className="test-block-title">Real voice results</h3>
            <p className="test-block-desc">
              Empirical trials recorded through real voice input across languages (Telugu/English/Mix) and background acoustic noise conditions (quiet/fan/street).
            </p>
            {hasVoiceTests ? (
              <div className="grid-summary-table-wrapper">
                <table className="grid-summary-table">
                  <thead>
                    <tr>
                      <th>Language</th>
                      {noiseLevels.map((n) => (
                        <th key={n.key}>{n.label}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {languages.map((l) => (
                      <tr key={l.key}>
                        <td className="grid-lang-cell">{l.label}</td>
                        {noiseLevels.map((n) => {
                          const val = gridMap[`${l.key}_${n.key}`] || 'Not yet measured';
                          return (
                            <td key={n.key} className="grid-score-cell">
                              {val}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-voice-tests-box">
                Not yet measured
              </div>
            )}
          </div>

          <div className="test-link-action">
            <button
              type="button"
              className="btn-view-tests"
              onClick={() => onNavigate('/tests')}
            >
              📊 Open Voice Testing & Telemetry Page →
            </button>
          </div>
        </section>
      </main>

      <footer className="about-footer">
        <p>Built solo by D Steven Son for the Great Indian AI Internship Challenge 2026</p>
        <p>
          <a
            href="https://github.com/stevenson-ai/VoiceQueue"
            target="_blank"
            rel="noopener noreferrer"
            className="github-link"
          >
            GitHub Repository
          </a>
        </p>
      </footer>
    </div>
  );
}
