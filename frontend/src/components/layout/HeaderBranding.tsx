"use client";

import React from "react";
import Link from "next/link";
import { BrandLogo } from "@/components/common/BrandLogo";
import { BRANDING } from "@/config/branding";

interface HeaderBrandingProps {
  className?: string;
}

/**
 * HeaderBranding renders the corporate dual-branding lockup:
 * 
 * Desktop:
 *   Verdictum AI  |  WYSETEK
 *        A Wysetek Product
 * 
 * Tablet:
 *   Verdictum AI  |  WYSETEK (compact, subtitle hidden where space is limited)
 * 
 * Mobile:
 *   Verdictum AI | WYSETEK or shortened Verdictum | WYSETEK (without subtitle, gracefully fits)
 */
export function HeaderBranding({ className = "" }: HeaderBrandingProps) {
  const productName = BRANDING.product.name;
  const companyShortName = BRANDING.company.shortName;
  const headerSubtitle = BRANDING.company.headerAttribution || "A Wysetek Product";

  return (
    <Link
      href="/agent-mission-control"
      className={`group flex flex-col items-center justify-center leading-none select-none transition-all duration-150 rounded px-2 py-0.5 focus:outline-none focus-visible:ring-1 focus-visible:ring-amber-500/50 ${className}`}
      title={`${productName} | ${companyShortName} — ${headerSubtitle}`}
      aria-label={`${productName} | ${companyShortName} — ${headerSubtitle}`}
      data-testid="header-dual-branding"
    >
      {/* Primary Dual Brand Lockup: Verdictum AI | WYSETEK */}
      <div className="flex items-center gap-1.5 sm:gap-2">
        {/* Official Verdictum AI Logo emblem */}
        <BrandLogo
          size={18}
          className="shrink-0 transition-transform duration-200 group-hover:scale-105"
          priority
        />

        {/* Verdictum AI Product Name */}
        <span className="font-semibold text-xs sm:text-[13px] tracking-wide text-slate-200 group-hover:text-slate-100 transition-colors">
          <span className="hidden min-[480px]:inline">{productName}</span>
          <span className="inline min-[480px]:hidden">Verdictum</span>
        </span>

        {/* Subtle Vertical Separator */}
        <span
          className="text-slate-600 dark:text-slate-600 text-xs font-light select-none px-0.5"
          aria-hidden="true"
        >
          |
        </span>

        {/* WYSETEK Corporate Name in bold, premium typography */}
        <span
          className="font-bold text-xs sm:text-[13px] tracking-widest text-slate-100 uppercase group-hover:text-amber-300 transition-colors"
          data-testid="header-branding-company"
        >
          {companyShortName}
        </span>
      </div>

      {/* Subtitle beneath primary branding: "A Wysetek Product" */}
      <span
        className="hidden lg:inline-block text-[8px] sm:text-[8.5px] font-mono tracking-wider text-amber-400/85 uppercase mt-0.5 font-medium group-hover:text-amber-300 transition-colors"
        data-testid="header-branding-subtitle"
      >
        {headerSubtitle}
      </span>
    </Link>
  );
}
