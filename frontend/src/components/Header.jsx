import React, { useEffect, useState } from "react";
import { BookOpenText, Leaf, RotateCcw } from "lucide-react";

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
        <button onClick={onReset} className="flex items-center gap-2.5 text-left text-white" title="Back to the top">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-leaf-400 to-forest-500 shadow-lg shadow-black/20">
            <Leaf className="h-5 w-5 text-forest-950" />
          </span>
          <span className="font-display text-lg font-semibold leading-none tracking-tight">EcoIQ</span>
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
