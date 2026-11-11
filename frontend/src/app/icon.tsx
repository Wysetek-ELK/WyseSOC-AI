import { ImageResponse } from "next/og";

export const size = {
  width: 48,
  height: 48,
};

export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "transparent",
        }}
      >
        <svg
          width="48"
          height="48"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M4 11 L24 20 L21 32 L10 26 Z"
            fill="#141016"
            stroke="#FFD700"
            strokeWidth="2.5"
            strokeLinejoin="round"
          />
          <path
            d="M60 11 L40 20 L43 32 L54 26 Z"
            fill="#141016"
            stroke="#FFD700"
            strokeWidth="2.5"
            strokeLinejoin="round"
          />
          <path
            d="M11 28 L32 58 L53 28 L46 24 L32 45 L18 24 Z"
            fill="#141016"
            stroke="#FF5500"
            strokeWidth="2.6"
            strokeLinejoin="round"
          />
          <path d="M30 12 H34 L34.8 44 H29.2 Z" fill="#FFD700" />
          <path d="M23 44 H41 L39 47 H25 Z" fill="#FF5500" />
          <circle cx="32" cy="10.5" r="2.6" fill="#FFD700" />
          <path
            d="M15 18 Q23.5 14 32 16 Q40.5 14 49 18"
            stroke="#FFD700"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <path d="M16 18.5 L11 33 M16 18.5 L21 33" stroke="#FDE68A" strokeWidth="1.6" />
          <path
            d="M9.5 33 H22.5 C21.8 38.5 19 40 16 40 C13 40 10.2 38.5 9.5 33 Z"
            fill="#FF8C00"
          />
          <path d="M48 18.5 L43 33 M48 18.5 L53 33" stroke="#FDE68A" strokeWidth="1.6" />
          <path
            d="M41.5 33 H54.5 C53.8 38.5 51 40 48 40 C45 40 42.2 38.5 41.5 33 Z"
            fill="#FF8C00"
          />
        </svg>
      </div>
    ),
    {
      ...size,
    }
  );
}

