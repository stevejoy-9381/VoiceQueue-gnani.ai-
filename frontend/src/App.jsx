import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import AboutPage from './AboutPage.jsx';
import ClinicDashboard from './ClinicDashboard.jsx';
import VoiceTests from './VoiceTests.jsx';
import AudioLab from './AudioLab.jsx';
import { API_BASE, getWebSocketUrl } from './config.js';
import {
  initMicrophoneStream,
  startAudioRecording,
  stopAudioRecording,
  closeMicrophoneStream,
  getMicrophoneDevices,
  runMicCheck,
} from './audioCapture.js';
import { resolveUserError, getErrorDetails } from './errorCatalog.js';

function getSavedMicId() {
  try {
    return localStorage.getItem('vq_mic_device') || '';
  } catch (e) {
    return '';
  }
}

function saveSavedMicId(id) {
  try {
    if (id) {
      localStorage.setItem('vq_mic_device', id);
    } else {
      localStorage.removeItem('vq_mic_device');
    }
  } catch (e) {}
}

// Minimal silent 1-sample 16-bit PCM WAV to unlock browser audio autoplay
const SILENT_WAV = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA';

// Safely retrieve or initialize session ID
function getOrCreateSessionId() {
  try {
    let sid = localStorage.getItem('vq_session_id');
    if (!sid) {
      sid = 'vq_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
      localStorage.setItem('vq_session_id', sid);
    }
    return sid;
  } catch (e) {
    return 'vq_' + Date.now();
  }
}

function getStoredTokenId() {
  try {
    const tid = localStorage.getItem('vq_token_id');
    return tid ? parseInt(tid, 10) : null;
  } catch (e) {
    return null;
  }
}

function saveStoredTokenId(id) {
  try {
    if (id) {
      localStorage.setItem('vq_token_id', id.toString());
    } else {
      localStorage.removeItem('vq_token_id');
    }
  } catch (e) {}
}

function getStoredReply() {
  try {
    const rep = localStorage.getItem('vq_last_reply');
    return rep ? JSON.parse(rep) : null;
  } catch (e) {
    return null;
  }
}

function saveStoredReply(reply) {
  try {
    if (reply) {
      localStorage.setItem('vq_last_reply', JSON.stringify(reply));
    }
  } catch (e) {}
}

const UI_STRINGS = {
  te: {
    clinicTagline: 'క్లినిక్ టోకెన్ బుక్ చేయడానికి తెలుగు లేదా English లో మాట్లాడండి.',
    elderModeLabel: 'పెద్ద అక్షరాలు & ఎక్కువ కాంట్రాస్ట్ (Large text & high contrast)',
    slowAudioLabel: 'నెమ్మదిగా సమాధానం (Slower reply)',
    sayAgain: 'మళ్లీ చెప్పండి',
    tapHintPhone: 'ఫోన్‌లో, మాట్లాడటానికి మైక్‌ని ఒక్కసారి నొక్కండి, ఆపడానికి మళ్లీ నొక్కండి.',
    trySayingLabel: 'ఇలా చెప్పి చూడండి:',
    howItWorks: 'ఇది ఎలా పనిచేస్తుంది (How it works)',
    step1Title: 'మాట్లాడండి',
    step1Desc: 'తెలుగు, English లేదా Mix లో మాట్లాడటానికి SPACE పట్టుకోండి లేదా మైక్ నొక్కండి.',
    step2Title: 'మేము అర్థం చేసుకుంటాము',
    step2Desc: 'మీ టోకెన్ బుకింగ్, స్టేటస్ లేదా రద్దు అభ్యర్థనలను సిస్టమ్ గుర్తిస్తుంది.',
    step3Title: 'సమాధానం వినండి',
    step3Desc: 'సహాయకుడు సమాధానం చెబుతాడు మరియు మీ టోకెన్ వెంటనే బుక్ అవుతుంది.',
    syntheticNote: 'నిజమైన ఫోన్ నంబర్లు లేదా వ్యక్తిగత వివరాలు చెప్పవద్దు. ఇది సింథటిక్ డేటాతో కూడిన డెమో.',
    micLabel: 'మైక్ (Mic):',
    micCheck: '🎙️ మైక్ చెక్ (Mic check)',
    micChecking: '🎙️ తనిఖీ చేస్తోంది (Checking)',
    aboutLink: 'వాయిస్‌క్యూ మరియు పరిమితుల గురించి (About VoiceQueue & Limitations) →',
    emptyTokenState: 'ఇంకా టోకెన్ లేదు. ఇలా చెప్పి చూడండి: రేపు టోకెన్ కావాలి',
    cancelConfirmPrompt: 'మీరు టోకెన్ రద్దు చేయాలనుకుంటున్నారా?',
    yesBtn: 'అవును (Yes)',
    noBtn: 'వద్దు (No)',
    micHint: 'మాట్లాడటానికి SPACE నొక్కి పట్టుకోండి. మైక్రోఫోన్ ఉన్న ఇయర్‌ఫోన్లు బాగా పనిచేస్తాయి.',
    instruction: 'మాట్లాడటానికి నొక్కండి లేదా SPACE పట్టుకోండి',
    recordingHint: 'రికార్డింగ్... (పంపడానికి SPACE వదలండి లేదా నొక్కండి)',
    listening: 'వింటోంది (Listening)...',
    understanding: 'అర్థం చేసుకుంటోంది (Understanding)...',
    speakingReply: 'సమాధానం చెబుతోంది (Speaking reply)...',
    tapToHear: '🔊 సమాధానం వినడానికి నొక్కండి',
    testSound: '🔔 సౌండ్ టెస్ట్',
    youSaid: 'మీరు చెప్పినది',
    youSaidPlaceholder: 'మైక్ పట్టుకుని తెలుగు, English లేదా Mix లో మాట్లాడండి...',
    clinicReply: 'క్లినిక్ సమాధానం',
    replay: '🔊 మళ్లీ వినండి',
    replyPlaceholder: 'సహాయకుడి సమాధానం ఇక్కడ కనిపిస్తుంది మరియు వినిపిస్తుంది...',
    tokenLabel: 'టోకెన్',
    today: 'ఈరోజు',
    tomorrow: 'రేపు',
    doctorSeeing: 'డాక్టర్ ఇప్పుడు మిమ్మల్ని చూస్తున్నారు!',
    aheadInQueue: 'క్యూలో మీ ముందు:',
    patients: 'రోగులు ఉన్నారు',
    patient: 'రోగి ఉన్నారు',
    tokenIs: 'టోకెన్ స్థితి',
    tokenCalledAlert: 'మీ టోకెన్ పిలుస్తున్నారు. దయచేసి లోపలికి వెళ్లండి.',
    typeInstead: '⌨ మాట్లాడటానికి బదులుగా టైప్ చేయండి',
    hideType: '▲ టైపింగ్ దాచండి',
    typePlaceholder: 'ఉదా. repu token kavali / token status',
    send: 'పంపండి',
  },
  en: {
    clinicTagline: 'Speak in Telugu or English to book a clinic token.',
    elderModeLabel: 'Large text and high contrast',
    slowAudioLabel: 'Slower reply',
    sayAgain: 'Say that again',
    tapHintPhone: 'On a phone, tap the mic once to start and once to stop.',
    trySayingLabel: 'Try saying:',
    howItWorks: 'How it works',
    step1Title: 'Speak',
    step1Desc: 'Hold SPACE or tap the mic to speak in Telugu, English or Mix.',
    step2Title: 'We understand',
    step2Desc: 'Our system identifies your request to book, check status, or cancel.',
    step3Title: 'You hear the answer',
    step3Desc: 'The assistant speaks the answer and books your token immediately.',
    syntheticNote: 'Do not say real phone numbers or personal details. This is a demo with synthetic data.',
    micLabel: 'Mic:',
    micCheck: '🎙️ Mic check',
    micChecking: '🎙️ Checking',
    aboutLink: 'About VoiceQueue & Limitations →',
    emptyTokenState: 'No token yet. Try saying: I need a token for tomorrow',
    cancelConfirmPrompt: 'Do you want to cancel your token?',
    yesBtn: 'Yes',
    noBtn: 'No',
    micHint: 'Hold SPACE to speak. Earphones with a microphone work best.',
    instruction: 'Hold SPACE to speak. Earphones with a microphone work best.',
    recordingHint: 'Recording... (Tap or release SPACE to send)',
    listening: 'Listening...',
    understanding: 'Understanding...',
    speakingReply: 'Speaking reply...',
    tapToHear: '🔊 Tap to hear the reply',
    testSound: '🔔 Test sound',
    youSaid: 'You said',
    youSaidPlaceholder: 'Hold the mic and speak in Telugu, English or Mix...',
    clinicReply: 'Clinic Reply',
    replay: '🔊 Replay',
    replyPlaceholder: 'Assistant reply will appear and speak here...',
    tokenLabel: 'Token',
    today: 'TODAY',
    tomorrow: 'TOMORROW',
    doctorSeeing: 'Doctor is seeing you now!',
    aheadInQueue: 'Ahead in queue:',
    patients: 'patients',
    patient: 'patient',
    tokenIs: 'Token is',
    tokenCalledAlert: 'Your token is being called. Please go in.',
    typeInstead: '⌨ Type instead of speaking',
    hideType: '▲ Hide typing',
    typePlaceholder: 'e.g. need a token tomorrow / token status',
    send: 'Send',
  },
  mix: {
    clinicTagline: 'Clinic token book chesukovadaniki Telugu or English lo matladandi.',
    elderModeLabel: 'Large text & high contrast',
    slowAudioLabel: 'Slower reply (నెమ్మదిగా)',
    sayAgain: 'Say that again (మళ్లీ చెప్పండి)',
    tapHintPhone: 'Phone lo, tap mic once to start, tap again to stop.',
    trySayingLabel: 'Try saying:',
    howItWorks: 'How it works',
    step1Title: 'Speak',
    step1Desc: 'Hold SPACE or tap the mic to speak in Telugu, English or Mix.',
    step2Title: 'We understand',
    step2Desc: 'Our system identifies your booking, status, or cancellation request.',
    step3Title: 'You hear the answer',
    step3Desc: 'The assistant speaks the answer and books your token immediately.',
    syntheticNote: 'Do not say real phone numbers or personal details. This is a demo with synthetic data.',
    micLabel: 'Mic:',
    micCheck: '🎙️ Mic check',
    micChecking: '🎙️ Checking',
    aboutLink: 'About VoiceQueue & Limitations →',
    emptyTokenState: 'No token yet. Try saying: Repu token kavali',
    cancelConfirmPrompt: 'Token cancel cheyala? (Cancel token?)',
    yesBtn: 'Avunu (Yes)',
    noBtn: 'Vaddu (No)',
    micHint: 'Hold SPACE to speak. Earphones with a microphone work best.',
    instruction: 'Hold SPACE to speak. Earphones with a microphone work best.',
    recordingHint: 'Recording... (Tap or release SPACE to send)',
    listening: 'Listening...',
    understanding: 'Understanding...',
    speakingReply: 'Speaking reply...',
    tapToHear: '🔊 Tap to hear the reply',
    testSound: '🔔 Test sound',
    youSaid: 'You said (మీరు చెప్పినది)',
    youSaidPlaceholder: 'Hold the mic and speak in Telugu, English or Mix...',
    clinicReply: 'Clinic Reply',
    replay: '🔊 Replay',
    replyPlaceholder: 'Assistant reply will appear and speak here...',
    tokenLabel: 'Token',
    today: 'TODAY (ఈరోజు)',
    tomorrow: 'TOMORROW (రేపు)',
    doctorSeeing: 'Doctor is seeing you now!',
    aheadInQueue: 'Ahead in queue:',
    patients: 'patients',
    patient: 'patient',
    tokenIs: 'Token is',
    tokenCalledAlert: 'Your token is being called. Please go in.',
    typeInstead: '⌨ Type instead of speaking',
    hideType: '▲ Hide typing',
    typePlaceholder: 'e.g. repu token kavali / token status',
    send: 'Send',
  },
};

const TRY_SAYING_CHIPS = {
  te: [
    { label: 'రేపు టోకెన్ కావాలి', text: 'repu token kavali' },
    { label: 'నా వంతు ఎప్పుడు?', text: 'naa token status' },
    { label: 'టోకెన్ రద్దు చేయండి', text: 'token cancel cheyandi' },
  ],
  en: [
    { label: 'I need a token for tomorrow', text: 'I need a token for tomorrow' },
    { label: 'When is my turn', text: 'When is my turn' },
    { label: 'Cancel my token', text: 'Cancel my token' },
  ],
  mix: [
    { label: 'Repu token kavali', text: 'repu token kavali' },
    { label: 'When is my turn', text: 'when is my turn' },
    { label: 'Cancel my token', text: 'token cancel cheyandi' },
  ],
};

const WORD_TO_NUM = {
  // Telugu (1 to 20)
  'ఒకటి': 1, 'రెండు': 2, 'మూడు': 3, 'నాలుగు': 4, 'ఐదు': 5,
  'ఆరు': 6, 'ఏడు': 7, 'ఎనిమిది': 8, 'తొమ్మిది': 9, 'పది': 10,
  'పదకొండు': 11, 'పన్నెండు': 12, 'పదమూడు': 13, 'పద్నాలుగు': 14, 'పదిహేను': 15,
  'పదహారు': 16, 'పదిహేడు': 17, 'పద్దెనిమిది': 18, 'పందొమ్మిది': 19, 'ఇరవై': 20,
  // English (1 to 20)
  'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
  'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
  'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
  'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
};

function extractNumberFromReply(text, token) {
  // 1. Authoritative source: token object returned by the action
  if (token && token.number != null) return String(token.number);
  // 2. Check digits in reply text
  if (text) {
    const matchDigit = text.match(/\d+/);
    if (matchDigit) return matchDigit[0];
    // 3. Check number words in reply text: sort entries by word length descending so 'పదిహేడు' (17) matches before 'పది' (10)
    const lowerText = text.toLowerCase();
    const sortedEntries = Object.entries(WORD_TO_NUM).sort((a, b) => b[0].length - a[0].length);
    for (const [w, n] of sortedEntries) {
      if (text.includes(w) || lowerText.includes(w)) return String(n);
    }
  }
  return '1';
}

function getEnglishTranslation(replyText, token, serverTranslation) {
  if (serverTranslation) return serverTranslation;
  if (!replyText || !/[\u0C00-\u0C7F]/.test(replyText)) return null;

  // Single source of truth for the token number
  const num = token?.number != null ? String(token.number) : extractNumberFromReply(replyText, token);

  // Booked
  if (replyText.includes('బుక్ అయింది')) {
    const isToday = replyText.includes('ఈరోజు') || (!replyText.includes('రేపు') && token?.date === new Date().toISOString().split('T')[0]);
    return `Your token for ${isToday ? 'today' : 'tomorrow'} is number ${num}. Please come to the clinic on time.`;
  }
  // Turn now
  if (replyText.includes('మీ వంతు వచ్చింది')) {
    return `Your token number is ${num}. It is your turn now, please proceed to the doctor.`;
  }
  // Waiting ahead
  if (replyText.includes('వేచి ఉన్నారు')) {
    const ahead = token ? (token.ahead_count ?? 0) : 0;
    return `Your token number is ${num}. There are ${ahead} ${ahead === 1 ? 'patient' : 'patients'} waiting ahead of you.`;
  }
  // Cancel confirm
  if (replyText.includes('రద్దు చేయాలనుకుంటున్నారా')) {
    return `Are you sure you want to cancel token number ${num}? Please say yes or no.`;
  }
  // Cancelled
  if (replyText.includes('విజయవంతంగా రద్దు చేయబడింది') || replyText.includes('రద్దు చేయబడింది')) {
    return 'Your token has been cancelled successfully.';
  }
  // Cancel aborted
  if (replyText.includes('ఆపివేయబడింది')) {
    return 'Token cancellation was cancelled.';
  }
  // No token
  if (replyText.includes('ఎటువంటి యాక్టివ్ టోకెన్') || replyText.includes('కనుగొనబడలేదు')) {
    return 'No active token was found for you.';
  }
  // Greeting
  if (replyText.includes('వాయిస్ క్యూకి స్వాగతం')) {
    return 'Hello, welcome to Demo Clinic voice queue. You can book a token, check your status, or cancel your appointment.';
  }
  // Say again
  if (replyText.includes('స్పష్టంగా వినిపించలేదు') || replyText.includes('మళ్లీ చెప్పండి')) {
    return 'Sorry, I could not hear you clearly. Please say that again.';
  }
  // Unknown
  if (replyText.includes('మీ మాట అర్థం కాలేదు')) {
    return 'Sorry, I did not understand. Please say book token, status, or cancel.';
  }
  // Service paused
  if (replyText.includes('సేవ ప్రస్తుతం అందుబాటులో లేదు') || replyText.includes('తాత్కాలికంగా నిలిపివేయబడింది')) {
    return 'The service is currently paused. Please try again later.';
  }
  // Audio quality gate messages
  if (replyText.includes('చాలా తక్కువగా ఉంది') || replyText.includes('తక్కువ సమయం')) {
    return 'Speaking time was too short. Please speak clearly for at least one second.';
  }
  if (replyText.includes('చాలా పెద్దది')) {
    return 'Recording was too long. Please speak in a shorter sentence under 30 seconds.';
  }
  if (replyText.includes('చాలా తక్కువగా వినిపించింది') || replyText.includes('తక్కువ వాల్యూమ్')) {
    return 'Your voice is too quiet. Please speak louder or bring the microphone closer.';
  }
  if (replyText.includes('ఎటువంటి మాటలు వినిపించలేదు') || replyText.includes('మాటలు ఏవీ స్పష్టంగా లేవు')) {
    return 'No speech was detected. Please speak clearly into the microphone.';
  }
  if (replyText.includes('స్పష్టంగా లేదు లేదా పాడైంది')) {
    return 'Audio file is corrupt or unreadable. Please record again.';
  }
  if (replyText.includes('పరిమితి') || replyText.includes('డెమో')) {
    return 'Voice demo limit reached for now. Please watch the demo video or try typing.';
  }

  return 'Spoken reply provided in Telugu.';
}

export default function App() {
  const isClean = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('clean') === '1';
  const isDevMode = typeof window !== 'undefined' && window.location.search.includes('dev=1') && !isClean;

  const getPath = () => {
    const p = window.location.pathname;
    if (p.startsWith('/about')) return '/about';
    if (p.startsWith('/tests')) return '/tests';
    if (p.startsWith('/clinic')) return '/clinic';
    if (p.startsWith('/audio-lab')) return '/audio-lab';
    return '/';
  };

  // Navigation route: '/' (patient), '/clinic' (dashboard), '/tests' (voice tests), '/about' (about page), or '/audio-lab' (audio lab)
  const [currentPath, setCurrentPath] = useState(getPath);

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(getPath());
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  function navigateTo(path) {
    window.history.pushState({}, '', path);
    setCurrentPath(path);
  }

  // Session, language, and usage state
  const [sessionId] = useState(getOrCreateSessionId);
  const [language, setLanguage] = useState('te'); // 'te', 'en', 'mix'
  const [usage, setUsage] = useState(null);
  const [gnaniConfigured, setGnaniConfigured] = useState(true);
  const [voicesValid, setVoicesValid] = useState(true);
  const [invalidVoice, setInvalidVoice] = useState('');
  const isLimitReached = usage && usage.limit > 0 && usage.real_calls_today >= usage.limit;

  const t = UI_STRINGS[language] || UI_STRINGS.te;

  // Turn state
  const [state, setState] = useState('idle'); // 'idle', 'recording', 'processing', 'playing', 'error', 'confirm-cancel'
  const [transcript, setTranscript] = useState('');
  const [replyText, setReplyText] = useState('');
  const [replyLanguage, setReplyLanguage] = useState('');
  const [replyAudioB64, setReplyAudioB64] = useState('');
  const [replyEnglishTranslation, setReplyEnglishTranslation] = useState('');
  const [token, setToken] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [currentError, setCurrentError] = useState(null);
  const [tokenClearedNotice, setTokenClearedNotice] = useState('');
  const [tokenCalledAlert, setTokenCalledAlert] = useState(null);
  const [limitReason, setLimitReason] = useState(null);
  const [limitCounts, setLimitCounts] = useState(null);
  const [demoVideoUrl, setDemoVideoUrl] = useState('');
  const [voiceErrorReason, setVoiceErrorReason] = useState(null);

  const [showOwnerBar, setShowOwnerBar] = useState(() => {
    return typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('owner') === '1';
  });
  const [ownerKeyVal, setOwnerKeyVal] = useState(() => {
    try {
      return sessionStorage.getItem('owner_key') || sessionStorage.getItem('vq_owner_key') || '';
    } catch (e) {
      return '';
    }
  });

  const tokenRef = useRef(token);
  useEffect(() => {
    tokenRef.current = token;
  }, [token]);

  const activePollTokenIdRef = useRef(null);

  const languageRef = useRef(language);
  useEffect(() => {
    languageRef.current = language;
  }, [language]);

  function showError(errInput) {
    if (!errInput) {
      setCurrentError(null);
      setErrorMessage('');
      return;
    }
    setTokenClearedNotice('');
    const resolved = resolveUserError(errInput, language);
    setCurrentError(resolved);
    setErrorMessage(resolved.message);
  }

  function handleActionClick(actionType) {
    if (actionType === 'type_instead') {
      setShowTypeInput(true);
      showError(null);
    } else if (actionType === 'book_new') {
      saveStoredTokenId(null);
      setToken(null);
      setShowTypeInput(true);
      showError(null);
    } else {
      // try_again
      showError(null);
      setState('idle');
    }
  }

  // Keep displayed error message synced with current language
  useEffect(() => {
    if (currentError) {
      const updated = resolveUserError(currentError.code || currentError.rawDetails, language);
      setCurrentError(updated);
      setErrorMessage(updated.message);
    }
  }, [language]);

  // UI state
  const [showTypeInput, setShowTypeInput] = useState(false);
  const [typedText, setTypedText] = useState('');
  const [recordingSeconds, setRecordingSeconds] = useState(0.0);
  const [showAbout, setShowAbout] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const [micDevices, setMicDevices] = useState([]);
  const [selectedMicId, setSelectedMicId] = useState(getSavedMicId);
  const [activeMicName, setActiveMicName] = useState('');

  // P2-2: Elder-friendly mode (large text & high contrast toggle)
  const [elderContrast, setElderContrast] = useState(() => {
    try {
      return localStorage.getItem('vq_elder_contrast') === 'true';
    } catch (e) {
      return false;
    }
  });

  const handleToggleElderContrast = () => {
    setElderContrast((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('vq_elder_contrast', String(next));
      } catch (e) {}
      return next;
    });
  };

  // P2-2: Slower reply toggle (0.85x speed with preserved pitch)
  const [slowAudio, setSlowAudio] = useState(() => {
    try {
      return localStorage.getItem('vq_slow_audio') === 'true';
    } catch (e) {
      return false;
    }
  });

  const handleToggleSlowAudio = () => {
    setSlowAudio((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('vq_slow_audio', String(next));
      } catch (e) {}
      return next;
    });
  };

  // Keep shared audio element updated with slowAudio preference
  useEffect(() => {
    if (sharedAudioRef.current) {
      sharedAudioRef.current.playbackRate = slowAudio ? 0.85 : 1.0;
      sharedAudioRef.current.preservesPitch = true;
      if ('mozPreservesPitch' in sharedAudioRef.current) sharedAudioRef.current.mozPreservesPitch = true;
      if ('webkitPreservesPitch' in sharedAudioRef.current) sharedAudioRef.current.webkitPreservesPitch = true;
    }
  }, [slowAudio]);

  // Requirement 7: First-visit message (shown once, dismissed on click, stored in localStorage)
  const [showFirstVisitNotice, setShowFirstVisitNotice] = useState(() => {
    try {
      return localStorage.getItem('vq_visited') !== 'true';
    } catch (e) {
      return false;
    }
  });

  useEffect(() => {
    if (!showFirstVisitNotice) return;
    const dismissFirstVisit = () => {
      try {
        localStorage.setItem('vq_visited', 'true');
      } catch (e) {}
      setShowFirstVisitNotice(false);
    };
    window.addEventListener('click', dismissFirstVisit, { once: true });
    return () => window.removeEventListener('click', dismissFirstVisit);
  }, [showFirstVisitNotice]);

  // Refs for recording & audio
  const recordTimerRef = useRef(null);
  const sharedAudioRef = useRef(null);
  const currentBlobUrlRef = useRef(null);
  const isAudioUnlockedRef = useRef(false);
  const isRecordingRef = useRef(false);
  const isStartingRecordingRef = useRef(false);
  const stopRequestedRef = useRef(false);

  // Phase F / Audio Playback state
  const [playBlocked, setPlayBlocked] = useState(false);
  const [audioError, setAudioError] = useState('');
  const [audioServerError, setAudioServerError] = useState('');
  const [audioSource, setAudioSource] = useState('none');
  const [audioDuration, setAudioDuration] = useState(null);
  const [audioBytes, setAudioBytes] = useState(null);
  const [lastPlayResult, setLastPlayResult] = useState('-');
  const [stageTimesMs, setStageTimesMs] = useState(null);

  // Phase H: Mic check state
  const [micChecking, setMicChecking] = useState(false);
  const [micCountdown, setMicCountdown] = useState(3);
  const [micCheckResult, setMicCheckResult] = useState(null);

  // P2-4: Send raw audio flag (persisted in localStorage)
  const [sendRawAudio, setSendRawAudio] = useState(() => {
    try {
      return localStorage.getItem('vq_send_raw_audio') === 'true';
    } catch (e) {
      return false;
    }
  });

  function handleToggleRawAudio(val) {
    setSendRawAudio(val);
    try {
      localStorage.setItem('vq_send_raw_audio', val ? 'true' : 'false');
    } catch (e) {}
  }

  async function handleRunMicCheck() {
    if (micChecking) return;
    setMicChecking(true);
    setMicCheckResult(null);
    setMicCountdown(3);

    const timer = setInterval(() => {
      setMicCountdown((prev) => (prev > 1 ? prev - 1 : 1));
    }, 1000);

    try {
      const res = await runMicCheck(selectedMicId, (level) => {
        setMicLevel(level);
      });
      setMicCheckResult(res);
    } catch (err) {
      console.warn('Mic check error:', err);
      setMicCheckResult({ peak: 0, rms: 0, verdict: 'Too quiet' });
    } finally {
      clearInterval(timer);
      setMicChecking(false);
      setMicLevel(0);
    }
  }

  // Phase F: Unlock shared audio element on first user interaction (click or keydown)
  function unlockSharedAudio() {
    if (isAudioUnlockedRef.current) return;
    try {
      if (!sharedAudioRef.current) {
        sharedAudioRef.current = new Audio();
      }
      const audio = sharedAudioRef.current;
      audio.src = SILENT_WAV;
      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            audio.pause();
            isAudioUnlockedRef.current = true;
          })
          .catch(() => {});
      }
    } catch (e) {}
  }

  // Restore stored state and fetch usage on load
  useEffect(() => {
    // Hidden Owner Key prompt via ?owner=1
    try {
      if (typeof window !== 'undefined') {
        const params = new URLSearchParams(window.location.search);
        if (params.get('owner') === '1') {
          const key = window.prompt('Enter Owner Key:');
          if (key && key.trim()) {
            sessionStorage.setItem('owner_key', key.trim());
          }
          params.delete('owner');
          const cleanQuery = params.toString();
          const cleanUrl = window.location.pathname + (cleanQuery ? `?${cleanQuery}` : '');
          window.history.replaceState({}, '', cleanUrl);
        }
      }
    } catch (e) {}

    // Initialize ONE shared HTMLAudioElement
    if (!sharedAudioRef.current) {
      sharedAudioRef.current = new Audio();
    }

    const onFirstUserAction = () => {
      unlockSharedAudio();
    };
    window.addEventListener('click', onFirstUserAction, { once: true });
    window.addEventListener('keydown', onFirstUserAction, { once: true });

    const savedReply = getStoredReply();
    if (savedReply) {
      setTranscript(savedReply.transcript || '');
      setReplyText(savedReply.reply_text || '');
      setReplyLanguage(savedReply.reply_language || (savedReply.reply_text && /[\u0C00-\u0C7F]/.test(savedReply.reply_text) ? 'Telugu' : 'English'));
      setReplyAudioB64(savedReply.reply_audio_base64 || '');
      if (savedReply.token) {
        setToken(savedReply.token);
      }
      if (savedReply.english_translation) {
        setReplyEnglishTranslation(savedReply.english_translation);
      }
    }

    const savedTokenId = getStoredTokenId();
    if (savedTokenId) {
      fetchTokenDetails(savedTokenId);
    }

    fetchUsage();
    fetchHealth();
  }, []);

  async function fetchHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        const data = await res.json();
        const configured = Boolean(data.gnani_configured);
        setGnaniConfigured(configured);
        if (data.voices_valid !== undefined) {
          setVoicesValid(Boolean(data.voices_valid));
          setInvalidVoice(data.invalid_voice || data.bad_voice || '');
        }
        if (data.voice_error_reason) {
          setVoiceErrorReason(data.voice_error_reason);
        }
        if (!configured || data.voices_valid === false) {
          setShowTypeInput(true);
        }
      }
    } catch (e) {}
  }

  async function fetchUsage() {
    try {
      const res = await fetch(`${API_BASE}/usage`);
      if (res.ok) {
        const data = await res.json();
        setUsage(data);
        if (data.limit > 0 && data.real_calls_today >= data.limit) {
          setShowTypeInput(true);
        }
      }
    } catch (e) {}
  }

  const lastChangeTimeRef = useRef(Date.now());
  const lastTokenSnapshotRef = useRef('');

  // Requirement 2 & 3: Poll token details: 5s when visible, 30s when hidden;
  // stops on done/cancelled/no_show or after 10m of no change
  useEffect(() => {
    if (!token || !token.id) return;
    if (['done', 'cancelled', 'no_show'].includes(token.status)) return;
    if (token.status !== 'waiting' && token.status !== 'in_consult') return;

    let timerId = null;
    let isCancelled = false;

    // Reset snapshot when token or status changes
    const currentSnapshot = `${token.status}_${token.ahead_count ?? ''}`;
    if (lastTokenSnapshotRef.current !== currentSnapshot) {
      lastTokenSnapshotRef.current = currentSnapshot;
      lastChangeTimeRef.current = Date.now();
    }

    function schedulePoll() {
      if (isCancelled) return;
      // Requirement 3: Stop after 10 minutes (600,000 ms) of no change
      if (Date.now() - lastChangeTimeRef.current >= 10 * 60 * 1000) {
        return;
      }
      // Requirement 3: Poll slower when the tab is hidden (every 30 seconds) vs 5 seconds when visible
      const delay = document.hidden ? 30000 : 5000;
      timerId = setTimeout(async () => {
        if (!isCancelled) {
          await fetchTokenDetails(token.id);
          schedulePoll();
        }
      }, delay);
    }

    schedulePoll();

    function onVisibilityChange() {
      if (timerId) clearTimeout(timerId);
      schedulePoll();
    }

    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      isCancelled = true;
      if (timerId) clearTimeout(timerId);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [token?.id, token?.status]);

  async function fetchTokenDetails(tokenId) {
    if (!tokenId) return;
    const storedId = getStoredTokenId();
    if (!tokenRef.current && !storedId) {
      // Demo reset or token cleared: stop polling immediately to avoid 404
      return;
    }
    const requestedId = Number(tokenId);
    activePollTokenIdRef.current = requestedId;
    try {
      const res = await fetch(`${API_BASE}/tokens/${requestedId}`);
      // DO 5: Check if requestedId is still the current active token ID before processing response
      const currentActiveId = tokenRef.current?.id
        ? Number(tokenRef.current.id)
        : (getStoredTokenId() ? Number(getStoredTokenId()) : null);

      if (requestedId !== currentActiveId) {
        // Discard late poll response for old token
        return;
      }

      if (res.ok) {
        const data = await res.json();
        if (Number(data.id) !== currentActiveId) {
          // Double check: discard if returned data id doesn't match active id
          return;
        }
        const snapshot = `${data.status}_${data.ahead_count ?? ''}`;
        if (lastTokenSnapshotRef.current !== snapshot) {
          lastTokenSnapshotRef.current = snapshot;
          lastChangeTimeRef.current = Date.now();
        }
        setToken(data);
        tokenRef.current = data;
        // Requirement 2: Stop polling when status is done, cancelled or no_show
        if (['done', 'cancelled', 'no_show'].includes(data.status)) {
          try {
            localStorage.removeItem('vq_token_id');
          } catch (e) {}
        }
      } else if (res.status === 404) {
        if (requestedId !== currentActiveId) {
          return;
        }
        setToken(null);
        tokenRef.current = null;
        activePollTokenIdRef.current = null;
        try {
          localStorage.removeItem('vq_token_id');
        } catch (e) {}
        setTokenClearedNotice('Your token was cleared. Say or type a request to book a new one.');
      }
    } catch (e) {
      // Silently ignore background polling errors
    }
  }

  // Requirement 4: On Reset demo, broadcast a WebSocket message {type: 'demo_reset'}.
  // The patient page clears its saved token when it receives it.
  useEffect(() => {
    let ws = null;
    let reconnectTimer = null;
    let isDisposed = false;

    function connectWs() {
      if (isDisposed) return;
      try {
        const url = getWebSocketUrl('/ws/queue');
        ws = new WebSocket(url);

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'demo_reset') {
              setToken(null);
              tokenRef.current = null;
              activePollTokenIdRef.current = null;
              setTokenCalledAlert(null);
              try {
                localStorage.removeItem('vq_token_id');
                localStorage.removeItem('vq_last_reply');
              } catch (e) {}
              setTokenClearedNotice('Your token was cleared. Say or type a request to book a new one.');
            } else if (data.type === 'queue_changed') {
              const currentId = getStoredTokenId();
              if (currentId) {
                fetchTokenDetails(currentId);
              }
            } else if (data.type === 'token_called') {
              const currentId = getStoredTokenId();
              const myTok = tokenRef.current;
              const isMyToken =
                (myTok && Number(myTok.id) === Number(data.token_id)) ||
                (currentId && Number(currentId) === Number(data.token_id));

              if (isMyToken) {
                const calledNum = data.token_number || (myTok && myTok.number);
                setTokenCalledAlert({
                  tokenId: data.token_id,
                  number: calledNum,
                  time: Date.now(),
                });
                if (currentId) {
                  fetchTokenDetails(currentId);
                }
                // P3-2: Alert voice playback if server has ALERT_VOICE=true
                const curLang = languageRef.current || 'te-IN';
                fetch(`${API_BASE}/tokens/${data.token_id}/call-alert?lang=${curLang}`)
                  .then((res) => (res.ok ? res.json() : null))
                  .then((alertData) => {
                    if (alertData && alertData.alert_voice && alertData.audio_base64) {
                      playBase64Audio(alertData.audio_base64);
                    }
                  })
                  .catch(() => {});
              }
            }
          } catch (e) {}
        };

        ws.onclose = () => {
          if (!isDisposed) {
            reconnectTimer = setTimeout(connectWs, 3000);
          }
        };

        ws.onerror = () => {
          try {
            ws.close();
          } catch (e) {}
        };
      } catch (e) {}
    }

    connectWs();

    return () => {
      isDisposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) {
        ws.onclose = null;
        try {
          ws.close();
        } catch (e) {}
      }
    };
  }, []);

  // Phase B: Space key hold-to-talk, window blur, and page unload cleanup
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.code !== 'Space') return;
      if (e.repeat) return;
      const target = e.target;
      if (target && (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable)) {
        return;
      }
      e.preventDefault();
      handleStartRecording();
    }

    function handleKeyUp(e) {
      if (e.code !== 'Space') return;
      const target = e.target;
      if (target && (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable)) {
        return;
      }
      e.preventDefault();
      handleStopRecording();
    }

    function handleBlur() {
      if (isRecordingRef.current) {
        handleStopRecording();
      }
    }

    const handleUnload = () => {
      closeMicrophoneStream();
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    window.addEventListener('blur', handleBlur);
    window.addEventListener('beforeunload', handleUnload);
    window.addEventListener('pagehide', handleUnload);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      window.removeEventListener('blur', handleBlur);
      window.removeEventListener('beforeunload', handleUnload);
      window.removeEventListener('pagehide', handleUnload);
    };
  }, [gnaniConfigured, isLimitReached, state, selectedMicId, sessionId, language, token]);

  // Helper to convert base64 to Blob
  function b64ToBlob(b64Data, contentType = 'audio/wav') {
    const sliceSize = 1024;
    const byteCharacters = atob(b64Data);
    const bytesLength = byteCharacters.length;
    const slicesCount = Math.ceil(bytesLength / sliceSize);
    const byteArrays = new Array(slicesCount);

    for (let sliceIndex = 0; sliceIndex < slicesCount; ++sliceIndex) {
      const begin = sliceIndex * sliceSize;
      const end = Math.min(begin + sliceSize, bytesLength);
      const bytes = new Array(end - begin);
      for (let offset = begin, i = 0; offset < end; ++i, ++offset) {
        bytes[i] = byteCharacters.charCodeAt(offset);
      }
      byteArrays[sliceIndex] = new Uint8Array(bytes);
    }
    return new Blob(byteArrays, { type: contentType });
  }

  // Play audio using ONE shared HTMLAudioElement with Blob URL
  async function playBase64Audio(b64) {
    if (!b64) return;
    setPlayBlocked(false);
    setAudioError('');

    // Requirement 7: Use ONE shared audio element. Before playing a new reply:
    // pause current audio, set currentTime to 0, revoke old blob URL, then set new source.
    if (!sharedAudioRef.current) {
      sharedAudioRef.current = new Audio();
    }
    const audio = sharedAudioRef.current;
    try {
      audio.pause();
      audio.currentTime = 0;
    } catch (e) {}

    if (!currentBlobUrlRef.current) {
      let blobUrl = '';
      try {
        const blob = b64ToBlob(b64, 'audio/wav');
        blobUrl = URL.createObjectURL(blob);
        currentBlobUrlRef.current = blobUrl;
      } catch (err) {
        console.error('Failed to convert audio b64 to Blob:', err);
        setAudioError(getErrorDetails('audio_unavailable', language).message);
        setLastPlayResult(`Decode error: ${err.message}`);
        return;
      }

      audio.src = blobUrl;
      audio.load();
    }

    // P2-2: Apply playback rate (0.85x for slower reply) with preservesPitch
    try {
      audio.playbackRate = slowAudio ? 0.85 : 1.0;
      audio.preservesPitch = true;
      if ('mozPreservesPitch' in audio) audio.mozPreservesPitch = true;
      if ('webkitPreservesPitch' in audio) audio.webkitPreservesPitch = true;
    } catch (e) {}

    // Revoke URL when audio ends
    audio.onended = () => {
      setState((current) => (current === 'confirm-cancel' ? 'confirm-cancel' : 'idle'));
      setPlayBlocked(false);
      if (currentBlobUrlRef.current) {
        try {
          URL.revokeObjectURL(currentBlobUrlRef.current);
        } catch (e) {}
        currentBlobUrlRef.current = null;
      }
    };

    audio.onerror = (e) => {
      const code = audio.error ? audio.error.code : 'unknown';
      console.warn('Audio element error:', e, audio.error);
      setState((current) => (current === 'confirm-cancel' ? 'confirm-cancel' : 'idle'));
      setPlayBlocked(false);
      setAudioError(getErrorDetails('audio_unavailable', language).message);
      setLastPlayResult(`Audio error code ${code}`);
    };

    // Requirement 9: Wait for 'canplaythrough' event (with a 3 second timeout) before calling play()
    await new Promise((resolve) => {
      let settled = false;
      const timer = setTimeout(() => {
        if (!settled) {
          settled = true;
          cleanup();
          resolve();
        }
      }, 3000);

      const onCanPlay = () => {
        if (!settled) {
          settled = true;
          cleanup();
          resolve();
        }
      };

      const onError = () => {
        if (!settled) {
          settled = true;
          cleanup();
          resolve();
        }
      };

      function cleanup() {
        clearTimeout(timer);
        audio.removeEventListener('canplaythrough', onCanPlay);
        audio.removeEventListener('error', onError);
      }

      audio.addEventListener('canplaythrough', onCanPlay);
      audio.addEventListener('error', onError);
    });

    // Await play() promise and handle AbortError, NotAllowedError, other errors
    async function executePlay(isRetry = false) {
      try {
        setState('playing');
        await audio.play();
        setPlayBlocked(false);
        setLastPlayResult('Playing successfully');
      } catch (err) {
        if (err.name === 'AbortError' && !isRetry) {
          // AbortError: wait 150 ms and retry once
          console.warn('Audio play() AbortError: waiting 150ms and retrying once...');
          await new Promise((resolve) => setTimeout(resolve, 150));
          return executePlay(true);
        } else if (err.name === 'NotAllowedError') {
          // NotAllowedError: show large 'Tap to hear the reply' button
          console.warn('Audio play() was blocked by browser autoplay policy:', err);
          setState((current) => (current === 'confirm-cancel' ? 'confirm-cancel' : 'idle'));
          setPlayBlocked(true);
          setLastPlayResult('Blocked (NotAllowedError)');
        } else {
          // Any other error: show friendly message from catalog, keep raw in lastPlayResult & ?dev=1
          console.warn('Audio play() failed:', err);
          setState((current) => (current === 'confirm-cancel' ? 'confirm-cancel' : 'idle'));
          setPlayBlocked(false);
          const reason = err.message || err.name || 'Playback error';
          setAudioError(getErrorDetails('audio_unavailable', language).message);
          setLastPlayResult(`Error: ${reason}`);
        }
      }
    }

    await executePlay(false);
  }

  // Phase F: Small test sound to check speakers
  function playTestSound() {
    unlockSharedAudio();
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        const ctx = new AudioCtx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(440, ctx.currentTime);
        gain.gain.setValueAtTime(0.2, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.3);
        setTimeout(() => {
          try { ctx.close(); } catch (e) {}
        }, 500);
      }
    } catch (err) {
      console.warn('Test sound Web Audio error:', err);
    }
  }

  // Handle server turn response (voice in gives spoken reply + text; typed input gives text only)
  function handleTurnResponse(data, isVoiceTurn = false) {
    const determinedLang = data.reply_language || (data.reply_text && /[\u0C00-\u0C7F]/.test(data.reply_text) ? 'Telugu' : (data.reply_text ? 'English' : ''));
    setTranscript(data.transcript || '');
    setReplyText(data.reply_text || '');
    setReplyLanguage(determinedLang);
    setReplyAudioB64(data.reply_audio_base64 || '');
    setReplyEnglishTranslation(data.english_translation || '');
    setAudioSource(data.audio_source || 'none');
    setAudioDuration(data.audio_duration_seconds ?? null);
    setAudioBytes(data.audio_bytes ?? null);
    setAudioServerError(data.audio_error || '');
    setStageTimesMs(data.stage_times_ms || null);

    if (data.limit_reason) {
      setLimitReason(data.limit_reason);
    }
    if (data.limit_counts) {
      setLimitCounts(data.limit_counts);
    }
    if (data.voice_error_reason) {
      setVoiceErrorReason(data.voice_error_reason);
    }
    if (data.demo_video_url) {
      setDemoVideoUrl(data.demo_video_url);
    }

    if (data.intent === 'BOOK' && data.token) {
      // DO 4: Immediately set current token, save in localStorage (inside try/catch), replace token card, restart polling for NEW id only
      setToken(data.token);
      tokenRef.current = data.token;
      activePollTokenIdRef.current = Number(data.token.id);
      try {
        localStorage.setItem('vq_token_id', String(data.token.id));
      } catch (e) {}
      setTokenClearedNotice('');
    } else if (data.token) {
      setToken(data.token);
      tokenRef.current = data.token;
      activePollTokenIdRef.current = Number(data.token.id);
      saveStoredTokenId(data.token.id);
      setTokenClearedNotice('');
    } else if (!data.error && !data.error_code) {
      setTokenClearedNotice('');
    }

    saveStoredReply({
      transcript: data.transcript,
      reply_text: data.reply_text,
      reply_language: determinedLang,
      reply_audio_base64: data.reply_audio_base64,
      token: data.token,
      english_translation: data.english_translation,
    });

    if (data.error || data.error_code) {
      showError({ error: data.error, error_code: data.error_code, detail: data.error });
      setTokenClearedNotice('');
    } else {
      showError(null);
      setTokenClearedNotice('');
    }

    if (data.error_code === 'demo_limit' || data.error_code === 'credit_limit') {
      setShowTypeInput(true);
    }

    if (data.pending_confirm) {
      setState('confirm-cancel');
    } else {
      setState('idle');
    }

    // Spoken reply plays automatically after voice input; typed input gives text only
    if (isVoiceTurn && data.reply_audio_base64) {
      playBase64Audio(data.reply_audio_base64);
    }

    fetchUsage();
  }

  // Refresh available audio input devices
  async function refreshMicDevices() {
    try {
      const devs = await getMicrophoneDevices();
      setMicDevices(devs);
      if (devs.length > 0) {
        const saved = getSavedMicId();
        const matched = devs.find((d) => d.deviceId === saved) || devs[0];
        setSelectedMicId(matched.deviceId);
        setActiveMicName(matched.label);
      }
    } catch (e) {}
  }

  // Handle user switching microphone device
  async function handleDeviceChange(deviceId) {
    setSelectedMicId(deviceId);
    saveSavedMicId(deviceId);
    const matched = micDevices.find((d) => d.deviceId === deviceId);
    if (matched) setActiveMicName(matched.label);
    try {
      await initMicrophoneStream(deviceId);
    } catch (e) {}
  }

  // Start Web Audio capture
  async function handleStartRecording() {
    if (!gnaniConfigured) {
      showError('gnani_key_missing');
      setShowTypeInput(true);
      return;
    }
    if (isLimitReached) {
      showError('credit_limit');
      setShowTypeInput(true);
      return;
    }
    if (isRecordingRef.current || isStartingRecordingRef.current || state === 'processing') return;

    isStartingRecordingRef.current = true;
    stopRequestedRef.current = false;

    try {
      // Open stream once on first user action and keep alive
      await initMicrophoneStream(selectedMicId);
      await refreshMicDevices();

      // If user released the key while stream was initializing, stop immediately
      if (stopRequestedRef.current) {
        isStartingRecordingRef.current = false;
        stopRequestedRef.current = false;
        showError('too_short');
        setState('idle');
        return;
      }

      isRecordingRef.current = true;
      isStartingRecordingRef.current = false;
      setState('recording');
      setRecordingSeconds(0.0);
      setErrorMessage('');

      startAudioRecording((lvl) => {
        setMicLevel(lvl);
      });

      // 10 second auto-stop timer
      const startTime = Date.now();
      recordTimerRef.current = setInterval(() => {
        const elapsed = (Date.now() - startTime) / 1000;
        setRecordingSeconds(Math.min(elapsed, 10.0));
        if (elapsed >= 10.0) {
          handleStopRecording();
        }
      }, 100);
    } catch (err) {
      isStartingRecordingRef.current = false;
      isRecordingRef.current = false;
      setState('error');
      showError('mic_denied');
      setShowTypeInput(true);
    }
  }

  // Stop Web Audio capture with 300ms post-roll and quality validation
  async function handleStopRecording() {
    if (isStartingRecordingRef.current) {
      stopRequestedRef.current = true;
      return;
    }
    if (!isRecordingRef.current) return;
    isRecordingRef.current = false;

    if (recordTimerRef.current) {
      clearInterval(recordTimerRef.current);
      recordTimerRef.current = null;
    }

    setState('processing');
    setMicLevel(0);

    try {
      const wavBlob = await stopAudioRecording();
      if (wavBlob) {
        await sendAudioTurn(wavBlob);
      } else {
        setState('idle');
      }
    } catch (err) {
      console.warn('[Audio Capture Error]:', err.message);
      setState('idle');
      showError(err.message || 'audio_unavailable');
    }
  }

  // Toggle for mic button: tap to start / tap to stop
  function handleMicButtonClick() {
    if (state === 'recording') {
      handleStopRecording();
    } else if (state === 'idle' || state === 'error') {
      handleStartRecording();
    }
  }

  // Send 16kHz mono WAV audio turn to /voice/turn
  async function sendAudioTurn(wavBlob) {
    setState('processing');
    setErrorMessage('');

    try {
      const formData = new FormData();
      formData.append('audio', wavBlob, 'voice_input.wav');
      formData.append('language', language);
      formData.append('session_id', sessionId);
      if (token?.id) {
        formData.append('token_id', token.id.toString());
      }

      // P2-4: Switch to send raw audio (no cleaning)
      formData.append('clean', sendRawAudio ? 'false' : 'true');
      if (sendRawAudio) {
        formData.append('compare', 'true');
      }

      const headers = {};
      try {
        const ownerKey = sessionStorage.getItem('owner_key') || sessionStorage.getItem('vq_owner_key');
        if (ownerKey) {
          headers['X-Owner-Key'] = ownerKey;
        }
      } catch (e) {}

      const res = await fetch(`${API_BASE}/voice/turn`, {
        method: 'POST',
        headers: headers,
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        showError(errData || { error_code: 'server_error', detail: `Server HTTP ${res.status}` });
        setState('error');
        return;
      }

      const data = await res.json();
      // Requirement 5: Start loading audio element immediately as soon as response arrives
      if (data.reply_audio_base64) {
        try {
          if (!sharedAudioRef.current) {
            sharedAudioRef.current = new Audio();
          }
          const audio = sharedAudioRef.current;
          audio.pause();
          audio.currentTime = 0;
          if (currentBlobUrlRef.current) {
            try { URL.revokeObjectURL(currentBlobUrlRef.current); } catch (e) {}
            currentBlobUrlRef.current = null;
          }
          const blob = b64ToBlob(data.reply_audio_base64, 'audio/wav');
          const blobUrl = URL.createObjectURL(blob);
          currentBlobUrlRef.current = blobUrl;
          audio.src = blobUrl;
          audio.load();
        } catch (e) {
          console.warn('[Audio Preload Warning]:', e);
        }
      }
      // Voice turn plays spoken reply automatically
      handleTurnResponse(data, true);
    } catch (err) {
      console.warn('[Voice Turn Error]:', err);
      setState('error');
      showError(err.message || 'network_error');
    }
  }

  // Send text turn to /text/turn
  async function sendTextTurn(textToSend) {
    const text = (textToSend || typedText).trim();
    if (!text) return;

    setState('processing');
    setErrorMessage('');

    try {
      const payload = {
        text: text,
        language: language,
        session_id: sessionId,
        token_id: token?.id || null,
      };

      const headers = { 'Content-Type': 'application/json' };
      try {
        const ownerKey = sessionStorage.getItem('owner_key') || sessionStorage.getItem('vq_owner_key');
        if (ownerKey) {
          headers['X-Owner-Key'] = ownerKey;
        }
      } catch (e) {}

      const res = await fetch(`${API_BASE}/text/turn`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        showError(errData || { error_code: 'server_error', detail: `Server HTTP ${res.status}` });
        setState('error');
        return;
      }

      const data = await res.json();
      setTypedText('');
      // Typed input gives text only (Replay button can still speak it)
      handleTurnResponse(data, false);
    } catch (err) {
      console.warn('[Text Turn Error]:', err);
      setState('error');
      showError(err.message || 'network_error');
    }
  }

  // Replay stored audio
  function handleReplay() {
    if (replyAudioB64) {
      playBase64Audio(replyAudioB64);
    }
  }

  // If on /about, render the About Page view
  if (currentPath === '/about') {
    return <AboutPage onNavigate={(path) => navigateTo(path)} />;
  }

  // If on /clinic, render the Clinic Dashboard view
  if (currentPath === '/clinic') {
    return <ClinicDashboard />;
  }

  // If on /tests, render the Voice Testing & Telemetry view
  if (currentPath === '/tests') {
    return <VoiceTests onBack={() => navigateTo('/clinic')} />;
  }

  // If on /audio-lab, render the Audio Lab view (Phase H)
  if (currentPath === '/audio-lab') {
    return <AudioLab onBack={() => navigateTo(window.location.search.includes('dev=1') ? '/?dev=1' : '/')} />;
  }


  // Otherwise render the Patient Mobile View at '/'
  return (
    <div className={`app-viewport ${elderContrast ? 'elder-mode' : ''}`}>
      {/* First-visit audio enablement banner (Req 7) */}
      {showFirstVisitNotice && (
        <div
          className="first-visit-banner"
          role="status"
          onClick={() => {
            try {
              localStorage.setItem('vq_visited', 'true');
            } catch (e) {}
            setShowFirstVisitNotice(false);
          }}
        >
          Click once anywhere to allow sound, then hold SPACE.
        </div>
      )}

      {/* Gnani API Key Missing Banner */}
      {!gnaniConfigured && (
        <div className="patient-limit-banner">
          Gnani API key is missing. Add GNANI_API_KEY to backend/.env
        </div>
      )}

      {/* Voice Not Supported Banner */}
      {!voicesValid && (
        <div className="patient-limit-banner">
          Voice {invalidVoice} is not supported by timbre-v2.5. Fix backend/.env
        </div>
      )}

      {/* Paused Credit Limit Banner */}
      {isLimitReached && (
        <div className="patient-limit-banner">
          Voice is paused to save credits. Typing still works.
        </div>
      )}

      {/* Hidden Owner Key input bar via ?owner=1 */}
      {showOwnerBar && (
        <section
          className="owner-key-bar"
          style={{
            background: '#2C3E50',
            color: '#FFFFFF',
            padding: '8px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.85rem',
            borderBottom: '2px solid #1E293B',
          }}
          aria-label="Owner Key Configuration"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🔑 <strong>Owner Mode:</strong></span>
            <input
              type="password"
              placeholder="Enter OWNER_KEY"
              value={ownerKeyVal}
              onChange={(e) => {
                const val = e.target.value;
                setOwnerKeyVal(val);
                try {
                  if (val.trim()) {
                    sessionStorage.setItem('owner_key', val.trim());
                  } else {
                    sessionStorage.removeItem('owner_key');
                  }
                } catch (err) {}
              }}
              style={{
                padding: '4px 8px',
                borderRadius: '4px',
                border: '1px solid #CCC',
                color: '#111',
                fontSize: '0.85rem',
              }}
              data-testid="owner-key-input"
            />
            <span style={{ fontSize: '0.75rem', opacity: 0.85 }}>(Saved in sessionStorage only)</span>
          </div>
          <button
            type="button"
            onClick={() => setShowOwnerBar(false)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#FFF',
              cursor: 'pointer',
              fontSize: '1rem',
            }}
            title="Dismiss"
          >
            ✕
          </button>
        </section>
      )}

      {/* 1. Header & Language Switch */}
      <header className="app-header">
        <div className="top-nav-row">
          <div className="title-group">
            <h1 className="clinic-title">Demo Clinic</h1>
            <p className="clinic-tagline">{t.clinicTagline}</p>
          </div>
          <button
            type="button"
            className="clinic-nav-link"
            onClick={() => navigateTo('/clinic')}
            title="Open Live Clinic Dashboard"
          >
            Dashboard →
          </button>
        </div>
        <div className="lang-switcher" role="radiogroup" aria-label="Language selection">
          <button
            type="button"
            className={`lang-btn ${language === 'te' ? 'active' : ''}`}
            onClick={() => setLanguage('te')}
          >
            తెలుగు
          </button>
          <button
            type="button"
            className={`lang-btn ${language === 'en' ? 'active' : ''}`}
            onClick={() => setLanguage('en')}
          >
            English
          </button>
          <button
            type="button"
            className={`lang-btn ${language === 'mix' ? 'active' : ''}`}
            onClick={() => setLanguage('mix')}
          >
            Mix
          </button>
        </div>
      </header>

      {/* Elder-Friendly Accessibility Bar (Req 1, 2) */}
      <section className="accessibility-bar" aria-label="Accessibility options">
        <label className="a11y-toggle-label" htmlFor="a11y-elder-toggle">
          <input
            type="checkbox"
            id="a11y-elder-toggle"
            className="a11y-toggle-checkbox"
            checked={elderContrast}
            onChange={handleToggleElderContrast}
          />
          <span className="a11y-toggle-text">{t.elderModeLabel}</span>
        </label>
        <label className="a11y-toggle-label" htmlFor="a11y-slow-toggle">
          <input
            type="checkbox"
            id="a11y-slow-toggle"
            className="a11y-toggle-checkbox"
            checked={slowAudio}
            onChange={handleToggleSlowAudio}
          />
          <span className="a11y-toggle-text">{t.slowAudioLabel}</span>
        </label>
      </section>

      <main id="main-content" className="patient-main-content">
      {/* Try Saying Example Chips (Req 2) */}
      <div className="try-saying-container">
        <span className="try-saying-label">{t.trySayingLabel}</span>
        <div className="try-saying-chips">
          {(TRY_SAYING_CHIPS[language] || TRY_SAYING_CHIPS.te).map((chip, idx) => (
            <button
              key={idx}
              type="button"
              className="try-saying-chip"
              onClick={() => {
                setTypedText(chip.text);
                setShowTypeInput(true);
                sendTextTurn(chip.text);
              }}
              title="Click to send as text turn"
            >
              "{chip.label}"
            </button>
          ))}
        </div>
      </div>

      {/* Collapsible How It Works (Req 6) */}
      <details className="how-it-works-details">
        <summary className="how-it-works-summary">{t.howItWorks}</summary>
        <div className="how-it-works-content">
          <div className="how-step">
            <span className="how-step-num">1</span>
            <div>
              <strong>{t.step1Title}:</strong> {t.step1Desc}
            </div>
          </div>
          <div className="how-step">
            <span className="how-step-num">2</span>
            <div>
              <strong>{t.step2Title}:</strong> {t.step2Desc}
            </div>
          </div>
          <div className="how-step">
            <span className="how-step-num">3</span>
            <div>
              <strong>{t.step3Title}:</strong> {t.step3Desc}
            </div>
          </div>
          <p className="how-synthetic-note">{t.syntheticNote}</p>
        </div>
      </details>

      {/* Confirmation State Banner */}
      {state === 'confirm-cancel' && (
        <div className="confirm-banner" role="alertdialog" aria-label="Confirm token cancellation">
          <p className="confirm-prompt">{t.cancelConfirmPrompt}</p>
          <div className="confirm-actions">
            <button
              type="button"
              className="confirm-btn btn-yes"
              onClick={() => sendTextTurn('yes')}
            >
              {t.yesBtn}
            </button>
            <button
              type="button"
              className="confirm-btn btn-no"
              onClick={() => sendTextTurn('no')}
            >
              {t.noBtn}
            </button>
          </div>
        </div>
      )}

      {/* 2. Large Tap-to-Talk / Hold-to-Talk Mic Button */}
      <section className="mic-section" aria-label="Microphone recording section">
        <div className={`mic-wrapper ${state === 'recording' ? 'recording' : ''}`}>
          <button
            type="button"
            className={`mic-button ${state === 'recording' ? 'pulsing' : ''} ${isLimitReached || !gnaniConfigured ? 'mic-disabled' : ''}`}
            onClick={handleMicButtonClick}
            aria-label={state === 'recording' ? 'Tap to stop recording' : 'Tap to start recording'}
            disabled={state === 'processing' || isLimitReached || !gnaniConfigured}
          >
            <svg
              className="mic-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </svg>
          </button>
        </div>

        {/* Phase B: Live Level Meter while recording */}
        {state === 'recording' && (
          <div className="audio-level-meter" aria-label="Microphone volume level">
            <div
              className="audio-level-fill"
              style={{ width: `${Math.max(4, Math.round(micLevel * 100))}%` }}
            />
          </div>
        )}

        {/* Phase B: Microphone Selector and Active Device Display (Hidden in ?clean=1 recording mode) */}
        {!isClean && (
          <div className="mic-device-selector">
            <span className="mic-device-label">
              {t.micLabel} <strong>{activeMicName || 'Default'}</strong>
            </span>
            {micDevices.length > 1 && (
              <select
                id="mic-select"
                className="mic-select-dropdown"
                value={selectedMicId}
                onChange={(e) => handleDeviceChange(e.target.value)}
                aria-label="Select microphone"
              >
                {micDevices.map((d) => (
                  <option key={d.deviceId} value={d.deviceId}>
                    {d.label}
                  </option>
                ))}
              </select>
            )}
            {/* Phase F: Small Test sound link to check speakers */}
            <button
              type="button"
              className="test-sound-link"
              onClick={playTestSound}
              title="Play short beep to test speaker"
            >
              {t.testSound}
            </button>

            {/* Phase H: Mic check button (3s check, no Gnani call) */}
            <button
              type="button"
              className="mic-check-link"
              onClick={handleRunMicCheck}
              disabled={micChecking || state === 'recording'}
              title="Record 3 seconds to check mic volume and noise level"
            >
              {micChecking ? `${t.micChecking} (${micCountdown}s)...` : t.micCheck}
            </button>
          </div>
        )}

        {/* Phase H: Mic Check Verdict Card (Hidden in ?clean=1 recording mode) */}
        {!isClean && micCheckResult && (
          <div className={`mic-check-card ${micCheckResult.verdict.toLowerCase().replace(/\s+/g, '-')}`}>
            <div className="mic-check-header">
              <span className="mic-check-verdict">
                Verdict: <strong>{micCheckResult.verdict}</strong>
              </span>
              <button
                type="button"
                className="mic-check-close"
                onClick={() => setMicCheckResult(null)}
                aria-label="Close mic check"
              >
                ×
              </button>
            </div>
            <div className="mic-check-stats">
              <span>Level (RMS): {micCheckResult.rms}</span>
              <span>Peak: {micCheckResult.peak}</span>
            </div>
            <p className="mic-check-advice">
              {micCheckResult.verdict === 'Good' && 'Microphone level is clear and ready to use.'}
              {micCheckResult.verdict === 'Too quiet' && 'I can hardly hear you. Speak louder or move the mic closer (15-20 cm).'}
              {micCheckResult.verdict === 'Too loud' && 'Microphone input is clipping. Lower your input volume or move slightly away.'}
              {micCheckResult.verdict === 'Too noisy' && 'High background noise detected. Use earphones or move to a quieter room.'}
            </p>
          </div>
        )}

        <div className="mic-status" aria-live="polite" aria-atomic="true">
          {!gnaniConfigured ? (
            <p className="status-text paused-hint">Gnani API key missing — Use typing below</p>
          ) : isLimitReached ? (
            <p className="status-text paused-hint">Voice paused — Use typing below</p>
          ) : (
            <>
              {state === 'recording' && (
                <p className="status-text recording-text">{t.listening}</p>
              )}
              {state === 'processing' && <p className="status-text processing-text">{t.understanding}</p>}
              {state === 'playing' && <p className="status-text playing-text">{t.speakingReply}</p>}
              {state === 'idle' && (
                <>
                  <p className="status-text mic-hint-line">{t.micHint}</p>
                  <p className="tap-phone-note">{t.tapHintPhone}</p>
                </>
              )}
            </>
          )}
        </div>

        {currentError && (
          <div className="error-alert" role="alert">
            <div className="error-alert-body">
              <span className="error-alert-message">{currentError.message}</span>
              {currentError.suggestedAction && (
                <button
                  type="button"
                  className="error-alert-action-btn"
                  onClick={() => handleActionClick(currentError.actionType)}
                >
                  {currentError.suggestedAction}
                </button>
              )}
              {(currentError.code === 'demo_limit' || currentError.code === 'credit_limit') && (demoVideoUrl || (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_DEMO_VIDEO_URL)) && (
                <a
                  href={demoVideoUrl || import.meta.env.VITE_DEMO_VIDEO_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="demo-video-link-btn"
                  style={{
                    marginLeft: '8px',
                    display: 'inline-block',
                    padding: '4px 10px',
                    backgroundColor: '#1E40AF',
                    color: '#FFF',
                    borderRadius: '4px',
                    textDecoration: 'none',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                  }}
                >
                  ▶ Demo Video
                </a>
              )}
            </div>
            {isDevMode && (
              <div className="error-alert-dev">
                [dev: {currentError.code}] {currentError.rawDetails}
                {voiceErrorReason && ` | voice_error_reason: ${voiceErrorReason}`}
                {limitReason && ` | limit_reason: ${limitReason}`}
                {limitCounts && ` | counts: ip=${limitCounts.ip_count}/${limitCounts.ip_limit} sess=${limitCounts.sess_count}/${limitCounts.sess_limit} daily=${limitCounts.daily_count}/${limitCounts.daily_cap}`}
              </div>
            )}
          </div>
        )}

        <p className="privacy-synthetic-line" style={{ fontSize: '0.82rem', color: '#6F4E37', textAlign: 'center', marginTop: '12px', opacity: 0.85 }}>
          {t.syntheticNote}
        </p>
      </section>

      {/* 3. 'You said' Box */}
      <section className="card card-transcript" aria-label="Speech transcript">
        <h2 className="card-label">{t.youSaid}</h2>
        <p className="card-content">
          {transcript || <span className="placeholder-text">{t.youSaidPlaceholder}</span>}
        </p>
      </section>

      {/* 4. 'Reply' Box with Replay Button and Plain 'Say that again' */}
      <section className="card card-reply" aria-live="polite" aria-label="Clinic reply">
        <div className="card-header-row">
          <h2 className="card-label">{t.clinicReply}</h2>
          <div className="reply-actions-row">
            <button
              type="button"
              className="replay-btn"
              onClick={handleReplay}
              disabled={!replyAudioB64 || state === 'processing'}
              title="Replay reply voice"
            >
              {t.replay}
            </button>
            <button
              type="button"
              className="say-again-btn"
              onClick={handleReplay}
              disabled={!replyAudioB64 || state === 'processing'}
              title="Say that again"
            >
              🔊 {t.sayAgain}
            </button>
          </div>
        </div>
        <p className="card-content">
          {replyText || <span className="placeholder-text">{t.replyPlaceholder}</span>}
        </p>
        {getEnglishTranslation(replyText, token, replyEnglishTranslation) && (
          <p className="reply-translation">
            <span className="translation-tag">EN:</span> {getEnglishTranslation(replyText, token, replyEnglishTranslation)}
          </p>
        )}
        {replyText && replyLanguage && ((language === 'en' && replyLanguage.toLowerCase().startsWith('te')) || (language === 'te' && replyLanguage.toLowerCase().startsWith('en'))) && (
          <p className="reply-language-indicator" data-testid="reply-language-indicator">
            Reply language: {replyLanguage}
          </p>
        )}

        {/* Requirement 10: If there is no audio show 'Voice reply is not available for this answer' */}
        {!replyAudioB64 && replyText && currentError?.code !== 'demo_limit' && currentError?.code !== 'credit_limit' && (
          <div
            className="reply-audio-unavailable"
            style={{ fontSize: '0.85rem', color: '#6F4E37', marginTop: '10px' }}
          >
            Voice reply is not available for this answer
          </div>
        )}

        {/* Phase F: Autoplay blocked fallback button */}
        {playBlocked && replyAudioB64 && (
          <div className="tap-to-hear-container">
            <button
              type="button"
              className="tap-to-hear-btn"
              onClick={() => {
                setPlayBlocked(false);
                playBase64Audio(replyAudioB64);
              }}
              aria-label="Tap to hear reply audio"
            >
              {t.tapToHear}
            </button>
          </div>
        )}

        {/* Requirement 9: Audio play error under reply card */}
        {audioError && (
          <div className="reply-audio-error" role="alert" style={{ fontSize: '0.85rem', color: '#5C3D2E', marginTop: '6px' }}>
            {audioError}
          </div>
        )}

        {/* Requirement 12: Developer line, visible only with ?dev=1 */}
        {isDevMode && (
          <div
            className="dev-audio-line"
            style={{
              marginTop: '10px',
              paddingTop: '6px',
              borderTop: '1px dashed #D4C3B3',
              fontSize: '0.78rem',
              color: '#6F4E37',
              opacity: 0.9,
              fontFamily: 'monospace',
            }}
          >
            [Dev Audio] source: {audioSource} | duration: {audioDuration != null ? audioDuration.toFixed(2) + 's' : '-'} | bytes: {audioBytes != null ? audioBytes : '-'} | play(): {lastPlayResult}{audioServerError ? ` | server: ${audioServerError}` : ''}
          </div>
        )}

        {/* P2-3: Latency stage breakdown, visible only with ?dev=1 */}
        {isDevMode && stageTimesMs && (
          <div
            className="dev-latency-line"
            style={{
              marginTop: '6px',
              fontSize: '0.78rem',
              color: '#6F4E37',
              opacity: 0.9,
              fontFamily: 'monospace',
              wordBreak: 'break-all',
            }}
          >
            [Dev Latency] total: {stageTimesMs.total != null ? stageTimesMs.total + 'ms' : '-'} | convert: {stageTimesMs.convert != null ? stageTimesMs.convert + 'ms' : '-'} | clean: {stageTimesMs.clean != null ? stageTimesMs.clean + 'ms' : '-'} | quality: {stageTimesMs.quality_gates != null ? stageTimesMs.quality_gates + 'ms' : '-'} | stt: {stageTimesMs.stt != null ? stageTimesMs.stt + 'ms' : '-'} | intent: {stageTimesMs.intent != null ? stageTimesMs.intent + 'ms' : '-'} | queue: {stageTimesMs.queue_action != null ? stageTimesMs.queue_action + 'ms' : '-'} | reply: {stageTimesMs.reply_choice != null ? stageTimesMs.reply_choice + 'ms' : '-'} | tts: {stageTimesMs.tts_or_cache != null ? stageTimesMs.tts_or_cache + 'ms' : '-'} | resp: {stageTimesMs.response_build != null ? stageTimesMs.response_build + 'ms' : '-'}
          </div>
        )}

        {/* Requirement 1: Limit diagnostic line, visible only with ?dev=1 */}
        {isDevMode && (limitReason || limitCounts) && (
          <div
            className="dev-limits-line"
            data-testid="dev-limits-line"
            style={{
              marginTop: '6px',
              fontSize: '0.78rem',
              color: '#8B0000',
              opacity: 0.95,
              fontFamily: 'monospace',
            }}
          >
            [Dev Limits] reason: {limitReason || 'none'} | ip_10m: {limitCounts?.ip_count ?? '-'}/{limitCounts?.ip_limit ?? '-'} | session: {limitCounts?.sess_count ?? '-'}/{limitCounts?.sess_limit ?? '-'} | daily: {limitCounts?.daily_count ?? '-'}/{limitCounts?.daily_cap ?? '-'} (reserve: {limitCounts?.reserve ?? '-'})
          </div>
        )}

        {/* P2-4: Switch 'Send raw audio' directly available in dev mode */}
        {isDevMode && (
          <div
            className="dev-raw-toggle"
            style={{
              marginTop: '6px',
              padding: '6px 10px',
              background: sendRawAudio ? '#FEF3C7' : '#F7F5F0',
              border: `1px solid ${sendRawAudio ? '#C8893B' : '#E0D6CC'}`,
              borderRadius: '6px',
              fontSize: '0.78rem',
              color: '#4A3525',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span>
              <strong>⚙️ Send raw audio (clean=false):</strong> {sendRawAudio ? 'ON (Raw audio)' : 'OFF (Cleaned)'}
            </span>
            <button
              type="button"
              onClick={() => handleToggleRawAudio(!sendRawAudio)}
              style={{
                background: sendRawAudio ? '#9E2A2B' : '#5C3D2E',
                color: '#FFF',
                border: 'none',
                borderRadius: '4px',
                padding: '3px 8px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              {sendRawAudio ? 'Switch to Cleaned' : 'Switch to Raw'}
            </button>
          </div>
        )}
      </section>

      {/* 5. Token Card */}
      {tokenCalledAlert && (
        <section
          className="token-called-banner"
          role="alert"
          aria-live="assertive"
          aria-label="Token called alert banner"
        >
          <div className="token-called-content">
            <span className="token-called-icon" aria-hidden="true">🔔</span>
            <div className="token-called-body">
              <h2 className="token-called-title">
                {t.tokenCalledAlert || 'Your token is being called. Please go in.'}
              </h2>
              {tokenCalledAlert.number && (
                <p className="token-called-sub">
                  {t.tokenLabel} #{tokenCalledAlert.number} &bull; {t.doctorSeeing || 'Doctor is seeing you now!'}
                </p>
              )}
            </div>
          </div>
          <button
            type="button"
            className="token-called-dismiss"
            onClick={() => setTokenCalledAlert(null)}
            aria-label="Dismiss alert"
          >
            ✕
          </button>
        </section>
      )}

      {tokenClearedNotice && !currentError && (
        <section
          className="card token-cleared-notice"
          role="status"
          style={{
            backgroundColor: '#F5EBDD',
            border: '1px solid #6F4E37',
            color: '#3B2418',
            textAlign: 'center',
            padding: '14px 16px',
            fontSize: '0.95rem',
            fontWeight: 500,
          }}
        >
          {tokenClearedNotice}
        </section>
      )}
      {token ? (
        <section className={`card token-card status-${token.status}`} aria-label="Booked token status card">
          <div className="token-header">
            <span className="token-day">{token.date === new Date().toISOString().split('T')[0] ? t.today : t.tomorrow}</span>
            <span className={`token-badge badge-${token.status}`}>{token.status.toUpperCase()}</span>
          </div>
          <div className="token-number-row">
            <span className="token-label">{t.tokenLabel}</span>
            <span className="token-number">#{token.number}</span>
          </div>
          {isDevMode && (
            <div
              className="dev-token-info"
              data-testid="dev-token-info"
              style={{ fontSize: '0.75rem', color: '#6F4E37', opacity: 0.8, marginTop: '2px' }}
            >
              dev: token_id={token.id}, token_number={token.number}
            </div>
          )}
          <div className="token-ahead-row">
            {token.status === 'in_consult' ? (
              <p className="ahead-highlight">{t.doctorSeeing}</p>
            ) : token.status === 'waiting' ? (
              <p className="ahead-text">
                {t.aheadInQueue} <strong>{token.ahead_count ?? 0}</strong> {token.ahead_count === 1 ? t.patient : t.patients}
              </p>
            ) : (
              <p className="ahead-inactive">{t.tokenIs} {token.status}</p>
            )}
          </div>
        </section>
      ) : (
        !tokenClearedNotice && (
          <section className="card card-empty-token" aria-label="No token booked yet">
            <p className="empty-token-text">{t.emptyTokenState}</p>
          </section>
        )
      )}

      {/* 6. 'Type instead' Accordion / Link */}
      <section className="type-section" aria-label="Text typing section">
        <button
          type="button"
          className="type-toggle-btn"
          onClick={() => setShowTypeInput(!showTypeInput)}
        >
          {showTypeInput ? t.hideType : t.typeInstead}
        </button>

        {showTypeInput && (
          <form
            className="type-form"
            onSubmit={(e) => {
              e.preventDefault();
              sendTextTurn();
            }}
          >
            <input
              type="text"
              id="type-text-input"
              className="type-input"
              placeholder={t.typePlaceholder}
              value={typedText}
              onChange={(e) => setTypedText(e.target.value)}
              disabled={state === 'processing'}
              autoFocus={isLimitReached}
              aria-label="Type message"
            />
            <button
              type="submit"
              className="type-send-btn"
              disabled={!typedText.trim() || state === 'processing'}
            >
              {t.send}
            </button>
          </form>
        )}
      </section>
      </main>

      {/* 7. Footer Link to /about and /audio-lab if dev=1 */}
      <footer className="app-footer">
        <button type="button" className="footer-link" onClick={() => navigateTo('/about')}>
          {t.aboutLink}
        </button>
        {typeof window !== 'undefined' && window.location.search.includes('dev=1') && (
          <button
            type="button"
            className="footer-link dev-link"
            onClick={() => navigateTo('/audio-lab?dev=1')}
            style={{ marginLeft: '16px', fontWeight: 'bold' }}
          >
            🔬 Audio Lab (Dev) →
          </button>
        )}
      </footer>
    </div>
  );
}
