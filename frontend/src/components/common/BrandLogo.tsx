"use client";

import React from "react";
import Image from "next/image";

interface BrandLogoProps {
  size?: number;
  className?: string;
  priority?: boolean;
  alt?: string;
}

/**
 * Renders the Verdictum AI emblem at crisp resolution
 * with transparent edges suited for both Obsidian Glass and Classic Slate themes.
 */
export function BrandLogo({
  size = 28,
  className = "",
  priority = false,
  alt = "Verdictum AI",
}: BrandLogoProps) {
  const src = size <= 64 ? "/verdictum-logo-sm.png" : "/verdictum-logo.png";

  return (
    <Image
      src={src}
      alt={alt}
      width={size}
      height={size}
      priority={priority}
      className={`shrink-0 object-contain select-none drop-shadow-[0_2px_10px_rgba(245,158,11,0.28)] ${className}`}
    />
  );
}

