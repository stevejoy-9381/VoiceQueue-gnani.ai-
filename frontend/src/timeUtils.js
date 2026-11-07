/**
 * Shared helper for displaying all times in IST (Asia/Kolkata).
 * Store UTC in database, convert only for display.
 */
export function formatTimeIST(dateOrStr = new Date()) {
  if (!dateOrStr) return '';
  let date;
  if (dateOrStr instanceof Date) {
    date = dateOrStr;
  } else if (typeof dateOrStr === 'string') {
    const s = dateOrStr.trim();
    if (s.includes('T') && !s.endsWith('Z') && !s.includes('+')) {
      date = new Date(`${s}Z`);
    } else {
      date = new Date(s);
    }
  } else {
    date = new Date(dateOrStr);
  }

  if (isNaN(date.getTime())) {
    return String(dateOrStr);
  }

  return date.toLocaleTimeString('en-US', {
    timeZone: 'Asia/Kolkata',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

