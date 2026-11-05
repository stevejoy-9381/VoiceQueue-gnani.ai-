import React, { useState, useEffect } from 'react';
import './AboutPage.css';
import { API_BASE } from './config.js';

export default function AboutPage({ onNavigate }) {
  const [groqConfigured, setGroqConfigured] = useState(false);
  const [voiceTestsSummary, setVoiceTestsSummary] = useState(null);

  useEffect(() => {
    // Check if Groq is configured
    fetch(`${API_BASE}/health`)
      .then((res) => (res.ok ? res.json() : {}))
      .then((data) => {
        setGroqConfigured(Boolean(data.groq_configured));
      })
      .catch(() => {});

    // Fetch real voice tests summary
    fetch(`${API_BASE}/voice-tests/summary`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        setVoiceTestsSummary(data);
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
              <h3>Gnani Prisma v3.0</h3>
              <p>Gnani Prisma v3.0 converts speech to text.</p>
            </div>

            <div className="model-box">
              <span className="model-badge">Text-to-Speech (TTS)</span>
              <h3>Gnani Timbre v2.5</h3>
              <p>Gnani Timbre v2.5 converts text to speech.</p>
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

        {/* 3. Honest Limitations List */}
        <section className="about-card">
          <h2 className="card-heading">Honest Limitations</h2>
          <p className="limitations-intro">
            Transparency is central to VoiceQueue. Please note the following design and technical boundaries:
          </p>
          <ul className="limitations-list">
            <li>
              <strong>Works best with short, clear sentences:</strong> Phrases like <em>"naaku repu token kavali"</em> or <em>"what is my token status"</em>
              yield optimal transcription and intent parsing. Lengthy narratives or tangential context may reduce accuracy.
            </li>
            <li>
              <strong>Heavy noise lowers accuracy:</strong> High background noise (loud traffic, heavy street horns, or loud ceiling fans)
              can degrade audio fidelity and STT recognition rates.
            </li>
            <li>
              <strong>Only three actions are supported:</strong> The current system handles only <em>Token Booking</em> (Today/Tomorrow),
              <em>Queue Status Check</em>, and <em>Token Cancellation</em> (with 60-second confirmation memory). Complex inquiries like doctor medical advice, prescription questions, or fee payments are out of scope.
            </li>
            <li>
              <strong>Rule-based intent understanding:</strong> The core parser prioritizes fast, deterministic, offline keyword matching
              (with day slot resolution). Novel colloquial slang or grammatical inversions not present in the vocabulary fall back to clarification prompts.
            </li>
            <li>
              <strong>Speaker sample:</strong> Accuracy was measured with a small number of speakers.
            </li>
          </ul>
        </section>

        {/* 4. Test Results */}
        <section className="about-card highlight-card">
          <h2 className="card-heading">Test Results</h2>
          
          {/* (a) Text rule test (no audio) */}
          <div className="test-block">
            <h3 className="test-block-title">Text rule test (no audio)</h3>
            <p className="test-block-desc">
              Written phrases are run through the intent rules without audio. These phrases were used to build the rules.
            </p>
            <div className="test-stat-row">
              <span className="test-stat-badge">Accuracy: 100.0% (45/45 phrases)</span>
              <span className="test-stat-sub">Evaluated across Telugu (15), English (15), and Mix (15)</span>
            </div>
          </div>

          <hr className="test-divider" />

          {/* (b) Real voice tests */}
          <div className="test-block">
            <h3 className="test-block-title">Real voice tests</h3>
            <p className="test-block-desc">
              Empirical trials recorded through real voice input across languages and background acoustic noise conditions (passed / total).
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
                          const val = gridMap[`${l.key}_${n.key}`] || '-';
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
                No real voice tests recorded yet
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
