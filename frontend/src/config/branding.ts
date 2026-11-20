/**
 * Centralized Branding Configuration
 *
 * Centralizes company identity, product titles, subtitles, and copyright
 * notices for Verdictum AI across both public and authenticated layouts.
 * Modify values here to update branding across the entire platform.
 */

export interface CompanyBrandingConfig {
  company: {
    fullName: string;
    shortName: string;
    developedByLabel: string;
    sidebarAttribution: string;
    headerAttribution: string;
    copyrightYear: number;
    copyrightNotice: string;
  };
  product: {
    name: string;
    title: string;
    platformSubtitle: string;
    agenticSubtitle: string;
    securityMotto: string;
  };
}

export const BRANDING: CompanyBrandingConfig = {
  company: {
    fullName: "Wysetek Systems Technologists Pvt. Ltd.",
    shortName: "WYSETEK",
    developedByLabel: "Developed & Operated by",
    sidebarAttribution: "by WYSETEK",
    headerAttribution: "A Wysetek Product",
    copyrightYear: 2026,
    copyrightNotice: "© 2026 Wysetek Systems Technologists Pvt. Ltd.",
  },
  product: {
    name: "Verdictum AI",
    title: "VERDICTUM AI",
    platformSubtitle: "Agentic SOC Intelligence Platform",
    agenticSubtitle: "Agentic SOC Intelligence",
    securityMotto: "Evidence-Driven Security Intelligence",
  },
} as const;

export const COMPANY_NAME = BRANDING.company.fullName;
export const SHORT_COMPANY_NAME = BRANDING.company.shortName;
export const HEADER_ATTRIBUTION = BRANDING.company.headerAttribution;
export const COPYRIGHT_NOTICE = BRANDING.company.copyrightNotice;
