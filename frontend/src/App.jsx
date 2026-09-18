import React, { useCallback, useEffect, useRef, useState } from "react";
import { ArrowDown, ClipboardList, MessagesSquare, TriangleAlert, X } from "lucide-react";
import { api } from "./lib/api.js";
import ChatPanel from "./components/ChatPanel.jsx";
import Dashboard from "./components/Dashboard.jsx";
import Examples from "./components/Examples.jsx";
import Header from "./components/Header.jsx";
import Hero from "./components/Hero.jsx";
import KnowledgeDrawer from "./components/KnowledgeDrawer.jsx";
import SiteForm from "./components/SiteForm.jsx";

export default function App() {
  const [health, setHealth] = useState(null);
  const [sites, setSites] = useState([]);
  const [panel, setPanel] = useState("chat");
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [kbOpen, setKbOpen] = useState(false);
  const resultRef = useRef(null);

  useEffect(() => {
    api.health().then(setHealth).catch((e) => setError(`Backend unreachable: ${e.message}`));
    api.sites().then(setSites).catch(() => {});
  }, []);

  const goTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  const run = async (request, userMessage) => {
    setBusy(true);
    setError(null);
    if (userMessage) setMessages((m) => [...m, { role: "user", ...userMessage }]);
    try {
      const r = await request();
      setResult(r);
      if (r.conversation_id) {
        setConversationId(r.conversation_id);
        setMessages((m) => [...m, { role: "assistant", result: r }]);
      }
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 150);
    } catch (e) {
      setError(e.message);
      if (userMessage) setMessages((m) => [...m, { role: "assistant", error: e.message }]);
    } finally {
      setBusy(false);
    }
  };

  const send = (text) => run(() => api.chat({ message: text, conversation_id: conversationId }), { content: text });

  const pickSite = (s) => {
    setPanel("chat");
    setMessages([]);
    setConversationId(null);
    run(() => api.chat({ message: s.example_message || "", site_id: s.site_id }),
      { content: s.example_message, site: s.name });
  };

  const reset = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setResult(null);
    setError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  return (
    <div className="min-h-full bg-sand-50">
      <Header onOpenKnowledge={() => setKbOpen(true)} onReset={reset} onNavigate={goTo} solid={!!result} />

      {error && (
        <div className="fixed inset-x-0 top-[60px] z-30 border-b border-clay-500/20 bg-clay-100 px-4 py-2 text-sm text-[#7d361c]">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-2">
            <span className="flex items-center gap-2"><TriangleAlert className="h-4 w-4" />{error}</span>
            <button onClick={() => setError(null)} aria-label="Dismiss"><X className="h-4 w-4" /></button>
          </div>
        </div>
      )}

      {/* 1 — full-screen landing */}
      <Hero health={health} onStart={() => goTo("ask")} onExamples={() => goTo("examples")} />

      {/* 2 — how it works, and the worked examples */}
      <section id="how" className="scroll-mt-20 bg-sand-50 py-16">
        <div id="examples" className="mx-auto max-w-6xl scroll-mt-20 px-4 sm:px-6">
          <Examples sites={sites} onPickSite={pickSite} busy={busy} />
        </div>
      </section>

      {/* 3 — ask about your own land */}
      <section id="ask" className="scroll-mt-20 border-t border-sand-200 bg-white py-16">
        <div className="mx-auto max-w-4xl px-4 sm:px-6">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <span className="label">Your turn</span>
              <h2 className="font-display text-3xl font-semibold text-ink-900">Tell EcoIQ about your land</h2>
              <p className="mt-1 max-w-xl text-sm text-ink-600">
                Write it in your own words, or fill in a short form. Anything you leave out is simply asked for.
              </p>
            </div>
            <div className="inline-flex shrink-0 rounded-xl bg-sand-100 p-1">
              {[["chat", MessagesSquare, "Write"], ["form", ClipboardList, "Fill a form"]].map(([id, Icon, label]) => (
                <button key={id} onClick={() => setPanel(id)}
                        className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold transition ${panel === id ? "bg-white text-forest-700 shadow-soft" : "text-ink-600 hover:text-ink-900"}`}>
                  <Icon className="h-4 w-4" /> {label}
                </button>
              ))}
            </div>
          </div>

          <div className="card overflow-hidden">
            {panel === "chat"
              ? <ChatPanel messages={messages} onSend={send} busy={busy} />
              : <SiteForm onSubmit={(body) => run(() => api.assess(body))} busy={busy} />}
          </div>
        </div>
      </section>

      {/* 4 — the answer */}
      <section id="results" ref={resultRef} className="scroll-mt-20 bg-sand-50 py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          {result ? (
            <>
              <div className="mb-5">
                <span className="label">The assessment</span>
                <h2 className="font-display text-3xl font-semibold text-ink-900">What EcoIQ found</h2>
                <p className="mt-1 max-w-2xl text-sm text-ink-600">
                  Scroll through: what is holding the land back, what to do in what order, the evidence behind it,
                  and how sure the system is.
                </p>
              </div>
              <Dashboard result={result} />
            </>
          ) : (
            <div className="mx-auto max-w-2xl rounded-2xl border border-dashed border-sand-200 bg-white px-6 py-12 text-center">
              <ArrowDown className="mx-auto h-5 w-5 animate-bounce text-ink-400" />
              <p className="mt-3 font-display text-lg font-semibold text-ink-900">Your results will appear here</p>
              <p className="mx-auto mt-1 max-w-md text-sm text-ink-600">
                Run one of the four examples, or describe your own land above. You will get the limiting factor,
                an ordered plan, the studies behind it and an honest confidence level.
              </p>
            </div>
          )}
        </div>
      </section>

      <footer className="border-t border-sand-200 bg-white py-8 text-center text-xs text-ink-400">
        EcoIQ · evidence-constrained environmental reasoning · rainfed cropland, peninsular India
      </footer>

      <KnowledgeDrawer open={kbOpen} onClose={() => setKbOpen(false)} health={health} />
    </div>
  );
}
