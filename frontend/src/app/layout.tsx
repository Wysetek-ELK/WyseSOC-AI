import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "@/context/AppContext";
import { Shell } from "@/components/layout/Shell";

export const metadata: Metadata = {
  title: "VERDICTUM AI | Agentic Triage & SOC Intelligence",
  description:
    "Evidence-Driven Security Intelligence · Verdictum AI Agentic Triage, Policy Governance, and Verification.",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "16x16 32x32 48x48", type: "image/x-icon" },
    ],
    shortcut: ["/favicon.svg"],
  },
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
