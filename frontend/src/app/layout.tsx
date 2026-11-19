import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "@/context/AppContext";
import { Shell } from "@/components/layout/Shell";
import { BRANDING } from "@/config/branding";

export const metadata: Metadata = {
  title: `${BRANDING.product.name} — ${BRANDING.product.platformSubtitle}`,
  description: `${BRANDING.product.securityMotto} · Enterprise ${BRANDING.product.name} Triage, Policy Governance, and Verification by ${BRANDING.company.fullName}.`,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark h-full" data-theme="obsidian" suppressHydrationWarning>
      <body className="h-full theme-body antialiased selection:bg-cyan-500/30 selection:text-cyan-200" suppressHydrationWarning>
        <AppProvider>
          <Shell>{children}</Shell>
        </AppProvider>
      </body>
    </html>
  );
}
