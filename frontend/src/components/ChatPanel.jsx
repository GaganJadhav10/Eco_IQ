import React, { useEffect, useRef, useState } from "react";
import { Bot, ChevronDown, CornerDownLeft, Mic, MicOff, Sparkles, Square, User, Volume2 } from "lucide-react";
import { speak, speechInputSupported, speechOutputSupported, stopSpeaking, useSpeechInput } from "../lib/speech.js";
import { spokenSummary } from "../lib/spoken.js";
import { SOURCE_LABEL, intLabel, varLabel } from "../lib/labels.js";
import Markdown from "./Markdown.jsx";
import { Badge, Spinner } from "./ui.jsx";

const SUGGESTIONS = [
  "Our wheat field near Beed gets about 520 mm of erratic rain, SOC is 0.32%, soil is loamy and bird numbers keep falling.",
  "I'm sure the pesticides are killing biodiversity on our groundnut farm.",
  "Soil carbon on our black cotton soil is falling. Would cover crops help?",
];

function Summary({ result }) {
  const a = result.assessment;
  if (a.status === "insufficient_data") {
    return (
      <div className="space-y-2">
        <p className="text-sm text-ink-900">
          I can’t recommend anything responsibly yet. <strong>{a.missing_variables.length} critical inputs</strong> are
          missing, and guessing them would make the advice unreliable.
        </p>
        {result.questions?.length > 0 && (
          <div className="rounded-xl border border-ochre-500/30 bg-ochre-100/60 p-3">
            <div className="label mb-1 text-[#8a5d05]">To continue, tell me</div>
            <ul className="list-disc space-y-1 pl-4 text-sm text-ink-900">
              {result.questions.map((q) => <li key={q}>{q}</li>)}
            </ul>
          </div>
        )}
      </div>
    );
  }
  return (
    <div className="space-y-2 text-sm text-ink-900">
      {result.focus?.map((f) => (
        <div key={f.intervention} className={`rounded-xl border p-3 ${f.in_sequence ? "border-forest-500/30 bg-leaf-50" : "border-ochre-500/30 bg-ochre-100/50"}`}>
          <div className="font-semibold">{intLabel(f.intervention)}</div>
          <p className="mt-0.5 text-ink-600">{f.verdict}</p>
          {f.rejected_claims?.length > 0 && (
            <p className="mt-1 text-xs text-ink-400">{f.rejected_claims.length} study/studies rejected for this site · see the Evidence tab</p>
          )}
        </div>
      ))}
      <p>
        The binding constraint is <strong>{varLabel(a.limiting_factor)}</strong>
        {a.suitability?.[a.limiting_factor] != null && <> (suitability {a.suitability[a.limiting_factor]})</>}.
        {a.drivers_ranked?.[0] && a.drivers_ranked[0].variable !== a.limiting_factor && (
          <> The strongest explanation for your concern is <strong>{varLabel(a.drivers_ranked[0].variable)}</strong>.</>
        )}
      </p>
      {a.hypothesis_note && <p className="rounded-lg bg-leaf-50 px-3 py-2 text-ink-600">{a.hypothesis_note}</p>}
      {a.sequence_detail?.length > 0 && (
        <ol className="space-y-1">
          {a.sequence_detail.slice(0, 4).map((s) => (
            <li key={s.intervention} className="flex items-center gap-2">
              <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-forest-700 text-[10px] font-bold text-white">{s.order}</span>
              <span className={s.stage.startsWith("defer") ? "text-[#8a5d05]" : ""}>{intLabel(s.intervention)}</span>
              <span className="text-xs text-ink-400">· {s.time_horizon}-term</span>
            </li>
          ))}
        </ol>
      )}
      <p className="text-xs text-ink-600">Confidence: <strong className="capitalize">{a.confidence.level}</strong>. See the full breakdown in the dashboard.</p>
      {result.improvement_questions?.length > 0 && (
        <div className="rounded-xl border border-dashed border-forest-500/30 bg-leaf-50 p-3">
          <div className="label mb-1 text-forest-700">To sharpen this, tell me</div>
          <ul className="list-disc space-y-1 pl-4 text-ink-900">
            {result.improvement_questions.map((q) => <li key={q}>{q}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function AssistantMessage({ m }) {
  const [open, setOpen] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const spokenOnce = useRef(false);
  const fields = Object.keys(m.result?.extraction?.fields || {});

  const toggleSpeech = () => {
    if (speaking) {
      stopSpeaking();
      setSpeaking(false);
      return;
    }
    setSpeaking(true);
    speak(spokenSummary(m.result), { onEnd: () => setSpeaking(false) });
  };

  useEffect(() => () => stopSpeaking(), []);

  // Asked by voice -> answer by voice, once per message.
  useEffect(() => {
    if (!m.speakAloud || !m.result || spokenOnce.current || !speechOutputSupported) return;
    spokenOnce.current = true;
    setSpeaking(true);
    speak(spokenSummary(m.result), { onEnd: () => setSpeaking(false) });
  }, [m.speakAloud, m.result]);
  return (
    <div className="flex animate-fade-up gap-2.5">
      <div className="mt-1 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-forest-800 text-leaf-300"><Bot className="h-4 w-4" /></div>
      <div className="min-w-0 flex-1 rounded-2xl rounded-tl-md border border-sand-200 bg-white p-3.5 shadow-soft">
        {m.error ? <p className="text-sm text-clay-500">{m.error}</p> : <Summary result={m.result} />}
        {fields.length > 0 && (
          <div className="mt-3 border-t border-dashed border-sand-200 pt-2">
            <div className="label mb-1.5">Understood from your message</div>
            <div className="flex flex-wrap gap-1">
              {fields.map((f) => (
                <Badge key={f} tone="leaf" title={`source: ${SOURCE_LABEL.user_text}`}>
                  {varLabel(f)}: {String(m.result.extraction.fields[f]).replace(/_/g, " ")}
                </Badge>
              ))}
            </div>
          </div>
        )}
        <div className="mt-2 flex flex-wrap items-center gap-3">
          {m.result?.narration?.text && (
            <button onClick={() => setOpen(!open)} className="inline-flex items-center gap-1 text-xs font-medium text-forest-600 hover:text-forest-700">
              <ChevronDown className={`h-3 w-3 transition ${open ? "rotate-180" : ""}`} />
              {open ? "Hide" : "Show"} full scientific narration
            </button>
          )}
          {speechOutputSupported && m.result && (
            <button onClick={toggleSpeech}
                    className={`inline-flex items-center gap-1 text-xs font-medium ${speaking ? "text-clay-500" : "text-forest-600 hover:text-forest-700"}`}>
              {speaking ? <Square className="h-3 w-3" /> : <Volume2 className="h-3.5 w-3.5" />}
              {speaking ? "Stop" : "Listen"}
            </button>
          )}
        </div>
        {open && <Markdown text={m.result.narration.text} className="mt-2 border-t border-sand-100 pt-2" />}
      </div>
    </div>
  );
}

export default function ChatPanel({ messages, onSend, busy }) {
  const [text, setText] = useState("");
  const listRef = useRef(null);
  const usedVoice = useRef(false);
  const mic = useSpeechInput({
    onResult: (spoken) => {
      usedVoice.current = true;
      setText((t) => (t ? `${t} ${spoken}` : spoken));
    },
  });

  useEffect(() => {
    // Scroll only the message list, never the page (keeps the dashboard in view on phones).
    const el = listRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  const submit = (e) => {
    e?.preventDefault();
    if (!text.trim() || busy) return;
    if (mic.listening) mic.stop();
    stopSpeaking();
    onSend(text.trim(), usedVoice.current);
    usedVoice.current = false;
    setText("");
  };

  return (
    <div className="flex flex-col">
      <div ref={listRef} className="scroll-thin max-h-[460px] min-h-[150px] space-y-4 overflow-y-auto px-4 py-4 sm:px-5">
        {messages.length === 0 && (
          <div className="animate-fade-up space-y-3">
            <div className="rounded-2xl bg-leaf-50 p-4">
              <div className="flex items-center gap-2 text-forest-700">
                <Sparkles className="h-4 w-4" />
                <span className="text-sm font-semibold">You don’t need to know everything</span>
              </div>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-600">
                Say whatever you know: the soil, the rain, the crop, and what worries you. EcoIQ asks for anything
                important that’s missing, and never guesses a number you didn’t give.
              </p>
            </div>
            <div className="label px-1">Or tap an example to see how it reads</div>
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => onSend(s)} disabled={busy}
                      className="block w-full rounded-xl border border-dashed border-sand-200 bg-sand-50 px-3 py-2 text-left text-sm text-ink-600 transition hover:border-forest-500 hover:bg-white hover:text-ink-900">
                “{s}”
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex animate-fade-up justify-end gap-2.5">
              <div className="max-w-[85%] rounded-2xl rounded-tr-md bg-forest-700 px-3.5 py-2.5 text-sm leading-relaxed text-white shadow-soft">
                {m.site && <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-leaf-300">{m.site}</div>}
                {m.content}
              </div>
              <div className="mt-1 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-sand-200 text-ink-600"><User className="h-4 w-4" /></div>
            </div>
          ) : (
            <AssistantMessage key={i} m={m} />
          ),
        )}
        {busy && (
          <div className="flex items-center gap-2.5 text-forest-600">
            <div className="grid h-7 w-7 place-items-center rounded-full bg-forest-800 text-leaf-300"><Bot className="h-4 w-4" /></div>
            <div className="rounded-2xl border border-sand-200 bg-white px-3.5 py-2.5 text-xs text-ink-600 shadow-soft">
              Reasoning over the knowledge base <Spinner className="ml-1 text-forest-500" />
            </div>
          </div>
        )}
      </div>

      <form onSubmit={submit} className="border-t border-sand-200 bg-white p-3 sm:p-4">
        <div className={`flex items-end gap-2 rounded-2xl border bg-sand-50 p-2 transition focus-within:ring-4 focus-within:ring-leaf-100 ${mic.listening ? "border-clay-500 ring-4 ring-clay-100" : "border-sand-200 focus-within:border-forest-500"}`}>
          <textarea value={mic.interim ? `${text}${text ? " " : ""}${mic.interim}` : text}
                    onChange={(e) => setText(e.target.value)} rows={2}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) submit(e); }}
                    placeholder={mic.listening ? "Listening… speak now" : "e.g. 600 mm rain, sandy soil, SOC 0.4%, groundnut monoculture…"}
                    className="max-h-40 min-h-[44px] flex-1 resize-none bg-transparent px-2 py-1 text-sm outline-none placeholder:text-ink-400" />
          {mic.supported && (
            <button type="button" onClick={mic.toggle} disabled={busy}
                    title={mic.listening ? "Stop the microphone" : "Speak instead of typing"}
                    aria-label={mic.listening ? "Stop the microphone" : "Speak instead of typing"}
                    className={`grid h-10 w-10 place-items-center rounded-xl border transition ${mic.listening ? "animate-pulse border-clay-500 bg-clay-500 text-white" : "border-sand-200 bg-white text-ink-600 hover:border-forest-500 hover:text-forest-700"}`}>
              {mic.listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
            </button>
          )}
          <button type="submit" disabled={busy || !text.trim()} className="btn-primary h-10 px-3" aria-label="Send">
            <CornerDownLeft className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-1.5 px-1 text-[11px] text-ink-400">
          {mic.error ? <span className="text-clay-500">{mic.error}</span>
            : mic.listening ? "Listening… tap the microphone again when you are done."
            : speechInputSupported ? "Enter to send · Shift+Enter for a new line · or tap the microphone to speak"
            : "Enter to send · Shift+Enter for a new line"}
        </p>
      </form>
    </div>
  );
}
