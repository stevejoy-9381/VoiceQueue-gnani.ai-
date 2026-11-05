import rawCatalog from '../../shared/error_catalog.json';

export const ERROR_CATALOG = rawCatalog;

export const EXPECTED_ERROR_CODES = [
  'mic_denied',
  'too_short',
  'too_quiet',
  'too_loud',
  'no_speech',
  'unclear_speech',
  'gnani_key_missing',
  'voice_invalid',
  'gnani_error',
  'credit_limit',
  'demo_limit',
  'network_error',
  'audio_unavailable',
  'token_not_found',
  'already_cancelled',
  'server_error',
];

/**
 * Normalizes UI language to 'te' or 'en'
 */
export function normalizeLanguage(lang) {
  if (!lang) return 'te';
  const l = lang.toString().toLowerCase().trim();
  if (l.startsWith('te')) return 'te';
  return 'en';
}

/**
 * Returns structured error details for an error code and language.
 */
export function getErrorDetails(code, lang = 'te') {
  const normLang = normalizeLanguage(lang);
  const entry = ERROR_CATALOG[code] || ERROR_CATALOG['server_error'] || {};
  const msgObj = entry.message || {};
  const actionObj = entry.suggested_action || {};

  return {
    code: code || 'server_error',
    message: msgObj[normLang] || msgObj['en'] || 'An error occurred.',
    suggestedAction: actionObj[normLang] || actionObj['en'] || 'Try again',
    actionType: entry.action_type || 'try_again',
  };
}

/**
 * Resolves any technical error, API response, or exception into a safe catalog error.
 * Raw details are preserved separately for ?dev=1 display only.
 */
export function resolveUserError(errorInput, lang = 'te') {
  let code = 'server_error';
  let rawDetails = '';

  if (typeof errorInput === 'string') {
    if (ERROR_CATALOG[errorInput]) {
      code = errorInput;
    } else {
      rawDetails = errorInput;
      const lower = errorInput.toLowerCase();
      if (lower.includes('mic') || lower.includes('permission') || lower.includes('notallowed')) {
        code = 'mic_denied';
      } else if (lower.includes('quiet')) {
        code = 'too_quiet';
      } else if (lower.includes('short')) {
        code = 'too_short';
      } else if (lower.includes('loud')) {
        code = 'too_loud';
      } else if (lower.includes('no speech') || lower.includes('no_speech')) {
        code = 'no_speech';
      } else if (lower.includes('unclear') || lower.includes('say_again')) {
        code = 'unclear_speech';
      } else if (lower.includes('gnani_key') || lower.includes('missing_gnani_key') || lower.includes('key is missing')) {
        code = 'gnani_key_missing';
      } else if (lower.includes('voice') && (lower.includes('invalid') || lower.includes('not supported'))) {
        code = 'voice_invalid';
      } else if (lower.includes('demo_limit') || lower.includes('demo limit')) {
        code = 'demo_limit';
      } else if (lower.includes('credit')) {
        code = 'credit_limit';
      } else if (lower.includes('network') || lower.includes('fetch') || lower.includes('connection')) {
        code = 'network_error';
      } else if (lower.includes('audio') && (lower.includes('play') || lower.includes('decode') || lower.includes('unavailable'))) {
        code = 'audio_unavailable';
      } else if (lower.includes('404') || lower.includes('not found')) {
        code = 'token_not_found';
      } else if (lower.includes('cancel')) {
        code = 'already_cancelled';
      } else if (lower.includes('gnani')) {
        code = 'gnani_error';
      }
    }
  } else if (errorInput && typeof errorInput === 'object') {
    const errCode = errorInput.error_code || errorInput.error || errorInput.code;
    const detail = errorInput.detail || errorInput.message || '';
    rawDetails = typeof detail === 'object' ? JSON.stringify(detail) : String(detail);

    if (errCode && ERROR_CATALOG[errCode]) {
      code = errCode;
    } else if (errCode) {
      const lower = String(errCode).toLowerCase();
      if (lower.includes('demo_limit')) code = 'demo_limit';
      else if (lower.includes('credit')) code = 'credit_limit';
      else if (lower.includes('gnani_key') || lower.includes('missing_gnani')) code = 'gnani_key_missing';
      else if (lower.includes('voice')) code = 'voice_invalid';
      else if (lower.includes('quiet')) code = 'too_quiet';
      else if (lower.includes('short')) code = 'too_short';
      else if (lower.includes('no_speech')) code = 'no_speech';
      else if (lower.includes('not_found') || lower.includes('404')) code = 'token_not_found';
      else if (lower.includes('gnani')) code = 'gnani_error';
      else if (lower.includes('network')) code = 'network_error';
    } else if (rawDetails) {
      return resolveUserError(rawDetails, lang);
    }
  }

  const details = getErrorDetails(code, lang);
  return {
    ...details,
    rawDetails: rawDetails || details.message,
  };
}

