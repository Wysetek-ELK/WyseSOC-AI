import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // Allow long-running Server 2 LLM / chat inference requests (up to 300s) proxied through Next rewrites
    proxyTimeout: 300_000,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
  async redirects() {
    return [
      {
        source: "/incidents",
        destination: "/ai-triage-workbench",
        permanent: false,
      },
      {
        source: "/incidents/:id",
        destination: "/ai-triage-workbench/:id",
        permanent: false,
      },
      {
        source: "/imports",
        destination: "/telemetry-hub",
        permanent: false,
      },
      {
        source: "/rules",
        destination: "/detection-intelligence",
        permanent: false,
      },
      {
        source: "/rules/:id",
        destination: "/detection-intelligence/:id",
        permanent: false,
      },
      {
        source: "/analyst-attention",
        destination: "/human-review-queue",
        permanent: false,
      },
      {
        source: "/prompt-studio",
        destination: "/agent-intelligence-studio",
        permanent: false,
      },
      {
        source: "/learning-history",
        destination: "/agent-memory",
        permanent: false,
      },
      {
        source: "/dry-run",
        destination: "/agent-simulation-lab",
        permanent: false,
      },
      {
        source: "/evaluation-reports",
        destination: "/verdict-intelligence",
        permanent: false,
      },
      {
        source: "/infrastructure",
        destination: "/inference-control",
        permanent: false,
      },
      {
        source: "/settings",
        destination: "/agent-configuration",
        permanent: false,
      },
      {
        source: "/admin",
        destination: "/governance-access",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
