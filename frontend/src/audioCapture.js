/**
 * AudioCapture: High quality Web Audio microphone capture for VoiceQueue.
 * Captures Float32 PCM samples, maintains a 400ms rolling pre-roll buffer,
 * captures 300ms post-roll, validates audio quality, resamples to 16kHz,
 * and builds a standard 16-bit mono WAV Blob.
 */

let audioContext = null;
let mediaStream = null;
let sourceNode = null;
let captureNode = null;
let isWorklet = false;

// Pre-roll rolling circular buffer (holds last 400ms of float32 samples)
let preRollQueue = [];
let preRollTotalSamples = 0;
let preRollMaxSamples = 0;

// Active recording buffers
let isRecording = false;
let recordedChunks = [];
let onLevelCallback = null;

const TARGET_SAMPLE_RATE = 16000;

function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

/**
 * Resamples Float32 audio samples from inSampleRate to 16,000 Hz via linear interpolation.
 */
export function resampleTo16k(samples, inSampleRate) {
  if (inSampleRate === TARGET_SAMPLE_RATE) {
    return samples;
  }
  const ratio = inSampleRate / TARGET_SAMPLE_RATE;
  const newLength = Math.round(samples.length / ratio);
  const result = new Float32Array(newLength);

  for (let i = 0; i < newLength; i++) {
    const pos = i * ratio;
    const idx = Math.floor(pos);
    const frac = pos - idx;
    const s1 = samples[idx] !== undefined ? samples[idx] : 0;
    const s2 = samples[idx + 1] !== undefined ? samples[idx + 1] : s1;
    result[i] = s1 + (s2 - s1) * frac;
  }
  return result;
}

/**
 * Encodes 16kHz Float32 mono samples into a 16-bit PCM RIFF/WAVE ArrayBuffer.
 */
export function encodeWAV(samples16k) {
  const numChannels = 1;
  const bitsPerSample = 16;
  const byteRate = TARGET_SAMPLE_RATE * numChannels * (bitsPerSample / 8);
  const blockAlign = numChannels * (bitsPerSample / 8);
  const dataSize = samples16k.length * (bitsPerSample / 8);
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  // RIFF header
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  writeString(view, 8, 'WAVE');

  // fmt subchunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // Subchunk1Size
  view.setUint16(20, 1, true); // AudioFormat (1 = PCM)
  view.setUint16(22, numChannels, true);
  view.setUint32(24, TARGET_SAMPLE_RATE, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);

  // data subchunk
  writeString(view, 36, 'data');
  view.setUint32(40, dataSize, true);

  // Write PCM audio samples clamped to [-1.0, 1.0]
  let offset = 44;
  for (let i = 0; i < samples16k.length; i++) {
    const s = Math.max(-1, Math.min(1, samples16k[i]));
    const val = s < 0 ? s * 0x8000 : s * 0x7fff;
    view.setInt16(offset, val, true);
    offset += 2;
  }

  return buffer;
}

/**
 * Handle incoming Float32 samples from AudioWorklet or ScriptProcessorNode.
 */
function handleAudioBlock(float32Data) {
  if (!float32Data || float32Data.length === 0) return;

  // Calculate live level (RMS) for meter
  if (onLevelCallback) {
    let sumSquares = 0;
    for (let i = 0; i < float32Data.length; i++) {
      sumSquares += float32Data[i] * float32Data[i];
    }
    const rms = Math.sqrt(sumSquares / float32Data.length);
    // Amplify slightly for responsive visual metering
    const level = Math.min(1.0, rms * 4.5);
    onLevelCallback(level);
  }

  if (isRecording) {
    recordedChunks.push(new Float32Array(float32Data));
  } else {
    // Keep 400ms rolling pre-roll buffer
    const copy = new Float32Array(float32Data);
    preRollQueue.push(copy);
    preRollTotalSamples += copy.length;

    while (preRollTotalSamples - preRollQueue[0].length >= preRollMaxSamples) {
      const removed = preRollQueue.shift();
      preRollTotalSamples -= removed.length;
    }
  }
}

/**
 * Returns available microphone devices.
 */
export async function getMicrophoneDevices() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
    return [];
  }
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices
      .filter((d) => d.kind === 'audioinput')
      .map((d, idx) => ({
        deviceId: d.deviceId,
        label: d.label || `Microphone ${idx + 1}`,
      }));
  } catch (e) {
    return [];
  }
}

/**
 * Initializes and opens the microphone stream once using Web Audio API.
 * Keeps the stream alive while the page is visible.
 */
export async function initMicrophoneStream(deviceId = null) {
  if (mediaStream && audioContext && audioContext.state !== 'closed') {
    // If deviceId hasn't changed or isn't specified, keep existing stream
    if (!deviceId) return audioContext;
  }

  // Close any existing stream before re-opening for a new device
  closeMicrophoneStream();

  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    throw new Error('Web Audio API is not supported in this browser.');
  }

  audioContext = new AudioContextClass();
  if (audioContext.state === 'suspended') {
    await audioContext.resume();
  }

  // 400ms rolling window sample count
  preRollMaxSamples = Math.round(audioContext.sampleRate * 0.4);
  preRollQueue = [];
  preRollTotalSamples = 0;

  const audioConstraints = {
    channelCount: 1,
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true,
  };
  if (deviceId) {
    audioConstraints.deviceId = { exact: deviceId };
  }

  mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: audioConstraints,
  });

  sourceNode = audioContext.createMediaStreamSource(mediaStream);

  // Attempt AudioWorklet first, fall back to ScriptProcessorNode
  try {
    const workletCode = `
      class VoiceQueueProcessor extends AudioWorkletProcessor {
        process(inputs) {
          const input = inputs[0];
          if (input && input[0]) {
            this.port.postMessage(input[0]);
          }
          return true;
        }
      }
      registerProcessor('voice-queue-processor', VoiceQueueProcessor);
    `;
    const blob = new Blob([workletCode], { type: 'application/javascript' });
    const blobUrl = URL.createObjectURL(blob);
    await audioContext.audioWorklet.addModule(blobUrl);
    URL.revokeObjectURL(blobUrl);

    captureNode = new AudioWorkletNode(audioContext, 'voice-queue-processor');
    captureNode.port.onmessage = (event) => {
      handleAudioBlock(event.data);
    };
    sourceNode.connect(captureNode);
    // Connect to destination via silent dummy gain to keep worklet executing continuously
    const dummyGain = audioContext.createGain();
    dummyGain.gain.value = 0;
    captureNode.connect(dummyGain);
    dummyGain.connect(audioContext.destination);

    isWorklet = true;
  } catch (workletErr) {
    // Fallback: ScriptProcessorNode (buffer size 4096)
    captureNode = audioContext.createScriptProcessor(4096, 1, 1);
    captureNode.onaudioprocess = (e) => {
      const channelData = e.inputBuffer.getChannelData(0);
      handleAudioBlock(channelData);
    };
    sourceNode.connect(captureNode);
    captureNode.connect(audioContext.destination);
    isWorklet = false;
  }

  return audioContext;
}

/**
 * Starts recording audio, prepending the 400ms pre-roll buffer.
 */
export function startAudioRecording(onLevel = null) {
  onLevelCallback = onLevel;
  recordedChunks = [];

  // Prepend all accumulated pre-roll chunks
  for (let i = 0; i < preRollQueue.length; i++) {
    recordedChunks.push(preRollQueue[i]);
  }
  preRollQueue = [];
  preRollTotalSamples = 0;

  isRecording = true;
}

/**
 * Stops recording audio with a 300ms post-roll, validates quality,
 * resamples to 16kHz mono, and returns a WAV Blob.
 */
export async function stopAudioRecording() {
  if (!isRecording) return null;

  // Keep recording for 300 ms post-roll to prevent cutting trailing syllables
  await new Promise((resolve) => setTimeout(resolve, 300));

  isRecording = false;
  onLevelCallback = null;

  if (recordedChunks.length === 0) {
    throw new Error('Too short, hold the key a little longer');
  }

  // Concatenate all recorded chunks into single Float32Array
  let totalLength = 0;
  for (let i = 0; i < recordedChunks.length; i++) {
    totalLength += recordedChunks[i].length;
  }

  const merged = new Float32Array(totalLength);
  let offset = 0;
  for (let i = 0; i < recordedChunks.length; i++) {
    merged.set(recordedChunks[i], offset);
    offset += recordedChunks[i].length;
  }
  recordedChunks = [];

  const inSampleRate = audioContext ? audioContext.sampleRate : 48000;
  const durationSec = totalLength / inSampleRate;

  // Check 1: Duration >= 0.5s
  if (durationSec < 0.5) {
    throw new Error('Too short, hold the key a little longer');
  }

  // Check 2 & 3: Peak level and clipping checks
  let maxPeak = 0;
  let clippingCount = 0;
  for (let i = 0; i < merged.length; i++) {
    const absVal = Math.abs(merged[i]);
    if (absVal > maxPeak) maxPeak = absVal;
    if (absVal >= 0.985) clippingCount++;
  }

  // Peak level very low check
  if (maxPeak < 0.02) {
    throw new Error('I can hardly hear you. Speak louder or move the microphone closer');
  }

  // Clipping check (> 100 clipped samples and > 0.8% of recording)
  if (clippingCount > 100 && clippingCount / merged.length > 0.008) {
    throw new Error('Too loud. Move a little away from the microphone');
  }

  // Resample to 16000 Hz
  const resampled16k = resampleTo16k(merged, inSampleRate);

  // Encode to 16-bit PCM WAV
  const wavBuffer = encodeWAV(resampled16k);
  return new Blob([wavBuffer], { type: 'audio/wav' });
}

/**
 * Stops all tracks and closes AudioContext.
 */
export function closeMicrophoneStream() {
  isRecording = false;
  onLevelCallback = null;

  if (captureNode) {
    try {
      captureNode.disconnect();
    } catch (e) {}
    captureNode = null;
  }
  if (sourceNode) {
    try {
      sourceNode.disconnect();
    } catch (e) {}
    sourceNode = null;
  }
  if (mediaStream) {
    try {
      mediaStream.getTracks().forEach((track) => track.stop());
    } catch (e) {}
    mediaStream = null;
  }
  if (audioContext && audioContext.state !== 'closed') {
    try {
      audioContext.close();
    } catch (e) {}
    audioContext = null;
  }
}

/**
 * Phase H: Records 3 seconds of audio to evaluate mic level and acoustic quality.
 * Returns { peak, rms, verdict } without calling Gnani.
 */
export async function runMicCheck(deviceId, onProgress) {
  if (!audioContext || audioContext.state === 'closed') {
    await initMicrophoneStream(deviceId);
  }
  if (audioContext && audioContext.state === 'suspended') {
    await audioContext.resume();
  }

  startAudioRecording((level) => {
    onProgress?.(level);
  });

  // Record for 3000 ms
  await new Promise((resolve) => setTimeout(resolve, 3000));

  isRecording = false;
  onLevelCallback = null;

  if (recordedChunks.length === 0) {
    return { peak: 0, rms: 0, verdict: 'Too quiet' };
  }

  let totalLen = 0;
  for (let i = 0; i < recordedChunks.length; i++) {
    totalLen += recordedChunks[i].length;
  }
  const merged = new Float32Array(totalLen);
  let offset = 0;
  for (let i = 0; i < recordedChunks.length; i++) {
    merged.set(recordedChunks[i], offset);
    offset += recordedChunks[i].length;
  }

  let peak = 0;
  let sumSq = 0;
  for (let i = 0; i < merged.length; i++) {
    const absVal = Math.abs(merged[i]);
    if (absVal > peak) peak = absVal;
    sumSq += merged[i] * merged[i];
  }
  const rms = Math.sqrt(sumSq / (merged.length || 1));

  let verdict = 'Good';
  if (peak < 0.05 || rms < 0.008) {
    verdict = 'Too quiet';
  } else if (peak >= 0.95 || rms > 0.30) {
    verdict = 'Too noisy';
  }

  return {
    peak: Math.round(peak * 1000) / 1000,
    rms: Math.round(rms * 1000) / 1000,
    verdict,
  };
}

