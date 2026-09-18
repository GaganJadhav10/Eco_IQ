import React from "react";
import { ArrowDown, ArrowRight, Database, ShieldCheck } from "lucide-react";

/**
 * Full-screen landing hero.
 *
 * Background: drop a file at `frontend/public/hero.mp4` (and optionally `hero.jpg` as the poster)
 * and it plays automatically behind the overlay. With no file present the gradient below shows
 * instead, so nothing breaks.
 */
export default function Hero({ onStart, onExamples, health }) {
  return (
    <section className="relative flex min-h-[100dvh] items-center justify-center overflow-hidden bg-forest-950">
      <video
        className="absolute inset-0 h-full w-full object-cover"
        autoPlay muted loop playsInline poster="/hero.jpg"
        onError={(e) => { e.currentTarget.style.display = "none"; }}
      >
        <source src="/hero.mp4" type="video/mp4" />
      </video>

      {/* gradient + texture: also the fallback when no video file exists */}
      <div className="absolute inset-0 bg-gradient-to-b from-forest-950/75 via-forest-950/55 to-forest-950/90" />
      <div className="absolute inset-0 bg-forest-950/25" />

      <div className="relative z-10 mx-auto w-full max-w-4xl px-5 py-24 text-center text-white sm:px-8">
        {/* Same lockup as the header, larger and in capitals: the mark is the E of ECOIQ. */}
        <span className="mb-7 flex items-baseline justify-center">
          <img src="/logo-e-light.png" alt="EcoIQ" className="h-[52px] w-auto shrink-0 sm:h-[64px]" />
          <span className="-ml-[6px] font-display text-[46px] font-semibold leading-none tracking-tight sm:-ml-[8px] sm:text-[57px]">
            CO<span className="text-ochre-500">IQ</span>
          </span>
        </span>
        <span className="chip border-leaf-400/30 bg-leaf-400/10 text-leaf-300 backdrop-blur">
          <ShieldCheck className="h-3 w-3" /> Every number traces to a sourced record
        </span>

        <h1 className="mt-6 font-display text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl lg:text-6xl">
          An environmental scientist for your farm
        </h1>

        <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-white/80 sm:text-lg">
          Tell it about your land in plain words. It works out the one thing holding biodiversity back,
          checks which studies actually apply to your soil and rainfall, and gives you the steps in the
          order they should happen.
        </p>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <button onClick={onStart}
                  className="inline-flex items-center gap-2 rounded-xl bg-leaf-400 px-6 py-3 text-sm font-semibold text-forest-950 shadow-lift transition hover:bg-leaf-300">
            Start with your land <ArrowRight className="h-4 w-4" />
          </button>
          <button onClick={onExamples}
                  className="inline-flex items-center gap-2 rounded-xl border border-white/25 bg-white/5 px-6 py-3 text-sm font-semibold text-white backdrop-blur transition hover:bg-white/15">
            See a worked example
          </button>
        </div>

        <div className="mt-12">
          <span className="rounded-lg border border-leaf-400/25 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-leaf-300/90">
            The science does not come from the language model
          </span>
          <div className="mt-4 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-white/70">
            <span className="inline-flex items-center gap-2">
              <Database className="h-4 w-4 text-leaf-300" />
              {health?.collections?.claims ?? 37} sourced claims in ChromaDB
            </span>
            <span>{health?.collections?.relationships ?? 25} causal links</span>
            <span>{health?.collections?.sources ?? 30} cited sources</span>
            <span>Same answer with the AI switched off</span>
          </div>
        </div>
      </div>

      <button onClick={onStart} aria-label="Scroll down"
              className="absolute bottom-6 left-1/2 z-10 -translate-x-1/2 rounded-full border border-white/20 bg-white/5 p-2 text-white/70 backdrop-blur transition hover:bg-white/15">
        <ArrowDown className="h-4 w-4 animate-bounce" />
      </button>
    </section>
  );
}
