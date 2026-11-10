"use client";

import React, { useState, useRef, useEffect } from "react";
import { HelpCircle, X } from "lucide-react";
import { GLOSSARY_ENTRIES } from "@/data/admin-guide/glossaryAndTroubleshootingData";

interface GlossaryTermProps {
  termId: string;
  children?: React.ReactNode;
  onJumpToGlossary?: (termId: string) => void;
}

export function GlossaryTerm({ termId, children, onJumpToGlossary }: GlossaryTermProps) {
  const [hovered, setHovered] = useState(false);
  const [pinned, setPinned] = useState(false);
  const containerRef = useRef<HTMLSpanElement>(null);
  const open = hovered || pinned;

  const entry = GLOSSARY_ENTRIES.find((g) => g.id === termId);

  useEffect(() => {
    if (!open) return;
    const handleOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setPinned(false);
        setHovered(false);
      }
    };
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setPinned(false);
        setHovered(false);
      }
    };
    document.addEventListener("mousedown", handleOutside);
    document.addEventListener("keydown", handleEsc);
    return () => {
      document.removeEventListener("mousedown", handleOutside);
      document.removeEventListener("keydown", handleEsc);
    };
  }, [open]);

  if (!entry) {
    return <span>{children || termId}</span>;
  }

  const handleTriggerClick = () => {
    if (pinned) {
      setPinned(false);
      setHovered(false);
    } else {
      setPinned(true);
    }
  };

  return (
    <span
      ref={containerRef}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="relative inline-block"
    >
      <button
        type="button"
        onClick={handleTriggerClick}
        className="inline-flex items-center gap-0.5 border-b border-dotted border-cyan-400/70 text-cyan-300 hover:text-cyan-200 font-medium cursor-help focus:outline-none focus-visible:ring-1 focus-visible:ring-cyan-400 rounded-xs"
        aria-expanded={open}
        aria-label={`Glossary definition for ${entry.term}`}
      >
        <span>{children || entry.term}</span>
        <HelpCircle className="h-3 w-3 text-cyan-400/80 inline shrink-0" />
      </button>

      {open && (
        <span
          role="tooltip"
          className="absolute left-0 bottom-full mb-1.5 z-50 w-72 sm:w-80 rounded-lg border border-cyan-500/40 bg-slate-950/95 p-3 text-left shadow-xl shadow-black/60 backdrop-blur-md block"
        >
          <span className="flex items-start justify-between gap-2 mb-1">
            <span className="text-[11px] font-bold text-cyan-300">{entry.term}</span>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setPinned(false);
                setHovered(false);
              }}
              className="text-slate-400 hover:text-slate-200 p-0.5"
              aria-label="Close definition"
            >
              <X className="h-3 w-3" />
            </button>
          </span>
          <span className="block text-[11px] text-slate-300 leading-relaxed mb-1.5">
            {entry.definition}
          </span>
          <span className="block text-[10px] font-mono text-slate-400 border-t border-slate-800 pt-1">
            {entry.codeReference}
          </span>
          {onJumpToGlossary && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setPinned(false);
                setHovered(false);
                onJumpToGlossary(entry.id);
              }}
              className="mt-1.5 text-[10px] font-semibold text-cyan-400 hover:text-cyan-300 underline"
            >
              View in Full Glossary →
            </button>
          )}
        </span>
      )}
    </span>
  );
}

