/**
 * Voice input and output using the browser's built-in Web Speech API.
 *
 * No extra library, no API key, nothing sent to a server: recognition and speech both run in the
 * browser. Chrome and Edge support both; Safari supports speaking; Firefox has no recognition, so
 * the microphone button simply hides itself there.
 *
 * The microphone needs HTTPS (or localhost), which Vercel provides.
 */
import { useCallback, useEffect, useRef, useState } from "react";

const Recognition = typeof window !== "undefined"
  ? window.SpeechRecognition || window.webkitSpeechRecognition
  : null;

export const speechInputSupported = !!Recognition;
export const speechOutputSupported = typeof window !== "undefined" && "speechSynthesis" in window;

// en-IN gives noticeably better results for Indian English than en-US.
const LANG = "en-IN";

export function useSpeechInput({ onResult } = {}) {
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState(null);
  const recognitionRef = useRef(null);
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;

  useEffect(() => {
    if (!Recognition) return undefined;
    const rec = new Recognition();
    rec.lang = LANG;
    rec.continuous = true;        // keep listening between sentences
    rec.interimResults = true;    // show words as they are spoken

    rec.onresult = (event) => {
      let finalText = "";
      let partial = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const chunk = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += chunk;
        else partial += chunk;
      }
      setInterim(partial);
      if (finalText.trim()) {
        setInterim("");
        onResultRef.current?.(finalText.trim());
      }
    };
    rec.onerror = (e) => {
      setError(e.error === "not-allowed"
        ? "Microphone blocked. Allow microphone access in your browser settings."
        : e.error === "no-speech" ? null : `Speech error: ${e.error}`);
      setListening(false);
    };
    rec.onend = () => setListening(false);

    recognitionRef.current = rec;
    return () => {
      rec.onresult = rec.onerror = rec.onend = null;
      try { rec.stop(); } catch { /* already stopped */ }
    };
  }, []);

  const start = useCallback(() => {
    setError(null);
    try {
      recognitionRef.current?.start();
      setListening(true);
    } catch { /* already listening */ }
  }, []);

  const stop = useCallback(() => {
    try { recognitionRef.current?.stop(); } catch { /* already stopped */ }
    setListening(false);
    setInterim("");
  }, []);

  const toggle = useCallback(() => (listening ? stop() : start()), [listening, start, stop]);

  return { supported: speechInputSupported, listening, interim, error, start, stop, toggle };
}

function pickVoice() {
  const voices = window.speechSynthesis.getVoices();
  return voices.find((v) => v.lang === LANG)
    || voices.find((v) => v.lang?.startsWith("en-IN"))
    || voices.find((v) => v.lang?.startsWith("en"))
    || null;
}

/** Speaks text aloud. Returns a stop function. */
export function speak(text, { onEnd } = {}) {
  if (!speechOutputSupported || !text) return () => {};
  const synth = window.speechSynthesis;
  synth.cancel();

  const say = () => {
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = pickVoice();
    if (voice) utterance.voice = voice;
    utterance.lang = LANG;
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.onend = () => onEnd?.();
    utterance.onerror = () => onEnd?.();
    synth.speak(utterance);
  };

  // Chrome populates the voice list asynchronously; speaking too early stays silent.
  if (synth.getVoices().length === 0) {
    const once = () => { synth.removeEventListener("voiceschanged", once); say(); };
    synth.addEventListener("voiceschanged", once);
    setTimeout(() => { synth.removeEventListener("voiceschanged", once); say(); }, 600);
  } else {
    say();
  }
  return () => synth.cancel();
}

export function stopSpeaking() {
  if (speechOutputSupported) window.speechSynthesis.cancel();
}
