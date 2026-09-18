import React from "react";

// Minimal renderer for narrator output: **bold**, *italic*, `code`, "- " bullets.
function inline(text, keyBase) {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g).filter(Boolean).map((p, i) => {
    const k = `${keyBase}-${i}`;
    if (p.startsWith("**")) return <strong key={k} className="font-semibold text-ink-900">{p.slice(2, -2)}</strong>;
    if (p.startsWith("`")) return <code key={k} className="rounded bg-sand-100 px-1 font-mono text-[0.85em]">{p.slice(1, -1)}</code>;
    if (p.startsWith("*") && p.length > 2) return <em key={k}>{p.slice(1, -1)}</em>;
    return <React.Fragment key={k}>{p}</React.Fragment>;
  });
}

export default function Markdown({ text = "", className = "" }) {
  const blocks = [];
  let list = null;
  text.split("\n").forEach((line, i) => {
    if (line.startsWith("- ")) {
      (list = list || []).push(<li key={i}>{inline(line.slice(2), i)}</li>);
      return;
    }
    if (list) {
      blocks.push(<ul key={`ul-${i}`} className="list-disc space-y-1 pl-5">{list}</ul>);
      list = null;
    }
    if (line.trim()) blocks.push(<p key={i}>{inline(line, i)}</p>);
  });
  if (list) blocks.push(<ul key="ul-end" className="list-disc space-y-1 pl-5">{list}</ul>);
  return <div className={`space-y-2 text-sm leading-relaxed text-ink-600 ${className}`}>{blocks}</div>;
}
