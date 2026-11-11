"use client";

import React, { useId } from "react";

export interface VerdictumLogoProps {
  size?: "sm" | "md" | "lg" | number;
  showWordmark?: boolean;
  showSubtitle?: boolean;
  className?: string;
}

const SIZE_MAP: Record<"sm" | "md" | "lg", number> = {
  sm: 30,
  md: 42,
  lg: 74,
};

export function VerdictumLogo({
  size = "md",
  showWordmark = true,
  showSubtitle,
  className = "",
}: VerdictumLogoProps) {
  const uid = useId().replace(/:/g, "");
  const iconPx = typeof size === "number" ? size : SIZE_MAP[size];
  const isCompact = iconPx <= 32;
  const isHero = iconPx >= 64;
  const shouldShowSubtitle =
    typeof showSubtitle === "boolean" ? showSubtitle : !isCompact;

  const goldMetalId = `vtm-gold-${uid}`;
  const rustGoldId = `vtm-rust-${uid}`;
  const darkArmorId = `vtm-armor-${uid}`;
  const emberGlowId = `vtm-ember-${uid}`;
  const beamMetalId = `vtm-beam-${uid}`;
  const stripePatternId = `vtm-stripes-${uid}`;
  const haloId = `vtm-halo-${uid}`;

  // Maintain wide winged heraldic crest proportions (120 x 96 viewBox)
  const svgWidth = Math.round(iconPx * 1.25);
  const svgHeight = iconPx;

  return (
    <div
      role="img"
      aria-label="Verdictum AI"
      className={`inline-flex ${
        isHero ? "flex-col items-center text-center gap-2.5" : "items-center gap-2"
      } select-none ${className}`}
    >
      {/* Logo 04 Crest: Cybernetic Winged V-Chevron + Scales of Justice */}
      <svg
        width={svgWidth}
        height={svgHeight}
        viewBox="0 0 120 96"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0 overflow-visible"
        aria-hidden="true"
      >
        <defs>
          {/* Metallic Gold Highlight Gradient */}
          <linearGradient id={goldMetalId} x1="12" y1="6" x2="108" y2="88" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FFF3B0" />
            <stop offset="28%" stopColor="#FFD700" />
            <stop offset="65%" stopColor="#F59E0B" />
            <stop offset="100%" stopColor="#C2410C" />
          </linearGradient>

          {/* Rust to Amber Bevel Gradient */}
          <linearGradient id={rustGoldId} x1="60" y1="8" x2="60" y2="92" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FFD700" />
            <stop offset="45%" stopColor="#FF8C00" />
            <stop offset="80%" stopColor="#FF5500" />
            <stop offset="100%" stopColor="#C2410C" />
          </linearGradient>

          {/* Deep Obsidian Tactical Armor Plate */}
          <linearGradient id={darkArmorId} x1="60" y1="10" x2="60" y2="86" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#261D24" />
            <stop offset="55%" stopColor="#141016" />
            <stop offset="100%" stopColor="#09070B" />
          </linearGradient>

          {/* Molten Ember Glow for Circuit Nodes & Scale Pans */}
          <linearGradient id={emberGlowId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#FFD700" />
            <stop offset="55%" stopColor="#FF8C00" />
            <stop offset="100%" stopColor="#FF5500" />
          </linearGradient>

          {/* Balance Beam Polished Brass */}
          <linearGradient id={beamMetalId} x1="26" y1="22" x2="94" y2="28" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#F59E0B" />
            <stop offset="30%" stopColor="#FFF0B8" />
            <stop offset="50%" stopColor="#FFD700" />
            <stop offset="70%" stopColor="#FFF0B8" />
            <stop offset="100%" stopColor="#C2410C" />
          </linearGradient>

          {/* Tactical Diagonal Wing Stripes */}
          <pattern id={stripePatternId} width="7" height="7" patternTransform="rotate(-38)" patternUnits="userSpaceOnUse">
            <rect width="7" height="7" fill="#171219" />
            <rect width="3.2" height="7" fill="#F59E0B" fillOpacity="0.72" />
          </pattern>

          {/* Soft Core Aura */}
          <radialGradient id={haloId} cx="50%" cy="46%" r="50%">
            <stop offset="0%" stopColor="#FF8C00" stopOpacity="0.32" />
            <stop offset="60%" stopColor="#C2410C" stopOpacity="0.1" />
            <stop offset="100%" stopColor="#000000" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Ambient Radial Glow Behind Crest */}
        <ellipse cx="60" cy="48" rx="52" ry="40" fill={`url(#${haloId})`} />

        {/* Micro-Telemetry Corner Crosshairs & Outer Circuit Brackets */}
        <g stroke="#F59E0B" strokeOpacity="0.55" strokeWidth="0.9">
          {/* Left tactical reticle */}
          <path d="M5 42 H11 M8 39 V45" />
          <path d="M12 24 H4 V30" fill="none" strokeOpacity="0.38" />
          {/* Right tactical reticle */}
          <path d="M109 42 H115 M112 39 V45" />
          <path d="M108 24 H116 V30" fill="none" strokeOpacity="0.38" />
          {/* Bottom chevron micro-dots */}
          <circle cx="8" cy="42" r="1" fill="#FF8C00" stroke="none" />
          <circle cx="112" cy="42" r="1" fill="#FF8C00" stroke="none" />
        </g>

        {/* 1. OUTER WINGED V-CHEVRON ARMOR */}
        {/* Left Upper Tactical Wing */}
        <path
          d="M8 15 L45 30 L40 50 L20 40 L12 25 Z"
          fill={`url(#${darkArmorId})`}
          stroke={`url(#${goldMetalId})`}
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
        {/* Left Diagonal Tactical Stripe Pocket */}
        <path
          d="M14 23 L41 33 L38 44 L21 36 Z"
          fill={`url(#${stripePatternId})`}
          stroke="#C2410C"
          strokeWidth="0.8"
          strokeOpacity="0.85"
        />
        {/* Left Wing Upper Metallic Blade Highlight */}
        <path
          d="M9 15 L45 30 L43 33 L12 20 Z"
          fill={`url(#${goldMetalId})`}
          fillOpacity="0.85"
        />

        {/* Right Upper Tactical Wing */}
        <path
          d="M112 15 L75 30 L80 50 L100 40 L108 25 Z"
          fill={`url(#${darkArmorId})`}
          stroke={`url(#${goldMetalId})`}
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
        {/* Right Diagonal Tactical Stripe Pocket */}
        <path
          d="M106 23 L79 33 L82 44 L99 36 Z"
          fill={`url(#${stripePatternId})`}
          stroke="#C2410C"
          strokeWidth="0.8"
          strokeOpacity="0.85"
        />
        {/* Right Wing Upper Metallic Blade Highlight */}
        <path
          d="M111 15 L75 30 L77 33 L108 20 Z"
          fill={`url(#${goldMetalId})`}
          fillOpacity="0.85"
        />

        {/* Lower Stepped V-Crest Backing & Outer Bevel */}
        <path
          d="M23 43 L60 86 L97 43 L87 38 L60 69 L33 38 Z"
          fill={`url(#${darkArmorId})`}
          stroke={`url(#${rustGoldId})`}
          strokeWidth="1.7"
          strokeLinejoin="round"
        />
        {/* Inner Chevron Shield Plate */}
        <path
          d="M32 39 L60 72 L88 39 L78 24 L60 28 L42 24 Z"
          fill={`url(#${darkArmorId})`}
          fillOpacity="0.95"
          stroke="#F59E0B"
          strokeWidth="1.1"
          strokeOpacity="0.65"
          strokeLinejoin="round"
        />
        {/* Outer Apex Point Tip */}
        <path
          d="M52 79 L60 90 L68 79 L60 84 Z"
          fill={`url(#${rustGoldId})`}
        />

        {/* 2. MICRO-TELEMETRY & CIRCUIT TRACES INSIDE CREST */}
        <g stroke="#FF8C00" strokeWidth="0.85" strokeOpacity="0.72" fill="none">
          <path d="M44 38 V52 L53 60" />
          <path d="M76 38 V52 L67 60" />
          <path d="M36 48 L47 59 V66" stroke="#FFD700" strokeOpacity="0.55" />
          <path d="M84 48 L73 59 V66" stroke="#FFD700" strokeOpacity="0.55" />
          <circle cx="44" cy="38" r="1.3" fill="#FFD700" stroke="none" />
          <circle cx="76" cy="38" r="1.3" fill="#FFD700" stroke="none" />
          <circle cx="47" cy="66" r="1.2" fill="#FF5500" stroke="none" />
          <circle cx="73" cy="66" r="1.2" fill="#FF5500" stroke="none" />
        </g>

        {/* 3. INTEGRATED SCALES OF JUSTICE */}
        {/* Central Vertical Pillar & Stepped Pedestal */}
        <path
          d="M58.2 21 H61.8 L62.6 67 H57.4 Z"
          fill={`url(#${goldMetalId})`}
        />
        {/* Pedestal Base */}
        <path
          d="M48 70 H72 L69 66.5 H51 Z"
          fill={`url(#${rustGoldId})`}
          stroke="#FFF3B0"
          strokeWidth="0.6"
        />
        <rect x="44.5" y="70" width="31" height="2.8" rx="1" fill={`url(#${goldMetalId})`} />

        {/* Top Finial Crown */}
        <path
          d="M60 11 L64 17 L60 22 L56 17 Z"
          fill={`url(#${goldMetalId})`}
          stroke="#FFF3B0"
          strokeWidth="0.7"
        />
        <circle cx="60" cy="17" r="1.6" fill="#FF5500" />

        {/* Symmetrical Curved Balance Beam */}
        <path
          d="M27 28.5 Q43 22 60 24.5 Q77 22 93 28.5"
          stroke={`url(#${beamMetalId})`}
          strokeWidth="2.8"
          strokeLinecap="round"
          fill="none"
        />
        {/* Beam Center Fulcrum Collar */}
        <circle cx="60" cy="24.5" r="3.2" fill="#18121B" stroke="#FFD700" strokeWidth="1.4" />
        <circle cx="60" cy="24.5" r="1.2" fill="#FF5500" />

        {/* Left & Right Suspension Pivot Rings */}
        <circle cx="29" cy="28" r="2.1" fill="#141016" stroke="#FFD700" strokeWidth="1.2" />
        <circle cx="91" cy="28" r="2.1" fill="#141016" stroke="#FFD700" strokeWidth="1.2" />

        {/* Left Scale Suspension Chords & Pan */}
        <g>
          <path
            d="M29 30 L20.5 51 M29 30 L37.5 51 M29 30 V51"
            stroke="#FDE68A"
            strokeWidth="1"
            strokeOpacity="0.88"
          />
          <path
            d="M18.5 51 H39.5 C38.5 57.5 34.5 60 29 60 C23.5 60 19.5 57.5 18.5 51 Z"
            fill={`url(#${emberGlowId})`}
            stroke="#FFF3B0"
            strokeWidth="0.9"
          />
          <ellipse cx="29" cy="51.2" rx="9.5" ry="1.4" fill="#FFF3B0" fillOpacity="0.6" />
        </g>

        {/* Right Scale Suspension Chords & Pan */}
        <g>
          <path
            d="M91 30 L82.5 51 M91 30 L99.5 51 M91 30 V51"
            stroke="#FDE68A"
            strokeWidth="1"
            strokeOpacity="0.88"
          />
          <path
            d="M80.5 51 H101.5 C100.5 57.5 96.5 60 91 60 C85.5 60 81.5 57.5 80.5 51 Z"
            fill={`url(#${emberGlowId})`}
            stroke="#FFF3B0"
            strokeWidth="0.9"
          />
          <ellipse cx="91" cy="51.2" rx="9.5" ry="1.4" fill="#FFF3B0" fillOpacity="0.6" />
        </g>
      </svg>

      {/* Typography Wordmark */}
      {showWordmark && (
        <div className={`flex flex-col ${isHero ? "items-center" : "items-start"} min-w-0`}>
          <div
            className={`inline-flex items-baseline gap-1 font-extrabold leading-none ${
              isHero ? "text-xl sm:text-2xl" : isCompact ? "text-xs" : "text-base"
            }`}
            style={{
              letterSpacing: "0.12em",
              filter: "drop-shadow(0 2px 6px rgba(0, 0, 0, 0.75))",
            }}
          >
            <span className="bg-gradient-to-b from-[#FFF3C4] via-[#FFD700] to-[#C2410C] bg-clip-text text-transparent">
              VERDICTUM
            </span>
            <span
              className={`font-black ${isHero ? "text-base sm:text-lg" : isCompact ? "text-[10px]" : "text-xs"}`}
              style={{
                color: "#FF5500",
                textShadow: "0 0 10px rgba(255, 85, 0, 0.55)",
              }}
            >
              AI
            </span>
          </div>

          {shouldShowSubtitle && (
            <span
              className="mt-1 font-mono uppercase tracking-[0.22em] leading-none whitespace-nowrap"
              style={{
                fontSize: "10px",
                color: "#D97706",
              }}
            >
              AI AGENTIC TRIAGE PLATFORM
            </span>
          )}
        </div>
      )}
    </div>
  );
}

