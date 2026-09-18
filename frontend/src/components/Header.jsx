import React, { useEffect, useState } from "react";
import { BookOpenText, RotateCcw } from "lucide-react";

export default function Header({ onOpenKnowledge, onReset, onNavigate, solid }) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const opaque = solid || scrolled;
  const NAV = [
    ["how", "How it works"],
    ["examples", "Examples"],
    ["ask", "Try it"],
  ];

  return (
    <header className={`fixed inset-x-0 top-0 z-40 transition-colors duration-300 ${opaque ? "border-b border-white/10 bg-forest-900/95 backdrop-blur" : "bg-transparent"}`}>
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        {/* The logo mark IS the E of the wordmark, so it sits flush against "coIQ". */}
        {/* In a baseline-aligned flex row an image's baseline is its bottom edge, so the foot of
            the E lands on the text baseline and the leaf rises like an ascender. */}
        <button onClick={onReset} className="flex items-baseline text-left text-white" title="Back to the top">
          <img src="/logo-e-light.png" alt="EcoIQ" className="h-[25px] w-auto shrink-0" />
          {/* pulled in by the leaf's overhang so the E and "co" read as one word */}
          <span className="-ml-[3px] font-display text-[22px] font-semibold leading-none tracking-tight">
            co<span className="text-ochre-500">IQ</span>
          </span>
        </button>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV.map(([id, label]) => (
            <button key={id} onClick={() => onNavigate(id)}
                    className="rounded-lg px-3 py-1.5 text-sm font-medium text-white/80 transition hover:bg-white/10 hover:text-white">
              {label}
            </button>
          ))}
          <button onClick={onOpenKnowledge}
                  className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium text-white/80 transition hover:bg-white/10 hover:text-white">
            <BookOpenText className="h-4 w-4" /> Knowledge base
          </button>
        </nav>

        <div className="flex items-center gap-2">
          <button onClick={() => onNavigate("ask")}
                  className="rounded-xl bg-leaf-400 px-4 py-2 text-sm font-semibold text-forest-950 transition hover:bg-leaf-300">
            Assess my land
          </button>
          <button onClick={onOpenKnowledge}
                  className="grid h-9 w-9 place-items-center rounded-xl border border-white/15 bg-white/5 text-white/80 transition hover:bg-white/10 md:hidden"
                  aria-label="Knowledge base">
            <BookOpenText className="h-4 w-4" />
          </button>
          <button onClick={onReset}
                  className="grid h-9 w-9 place-items-center rounded-xl border border-white/15 bg-white/5 text-white/80 transition hover:bg-white/10"
                  aria-label="Start over">
            <RotateCcw className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
