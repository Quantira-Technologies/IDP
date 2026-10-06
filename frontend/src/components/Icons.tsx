import React from "react";

const PATHS: Record<string, React.ReactNode> = {
  grid: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></>,
  file: <><path d="M6 2h8l4 4v16H6z" /><path d="M14 2v4h4" /></>,
  check: <><circle cx="12" cy="12" r="9" /><path d="M8.5 12.5l2.5 2.5 4.5-5" /></>,
  chart: <><path d="M4 20V4" /><path d="M4 20h16" /><rect x="7" y="11" width="3" height="6" /><rect x="12" y="7" width="3" height="10" /><rect x="17" y="13" width="3" height="4" /></>,
  shield: <><path d="M12 3l7 3v5c0 5-3.5 8-7 10-3.5-2-7-5-7-10V6z" /><path d="M9 12l2 2 4-4" /></>,
  users: <><circle cx="9" cy="8" r="3" /><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" /><path d="M16 11a3 3 0 100-6" /><path d="M21 20c0-2.5-1.6-4.6-4-5.5" /></>,
  history: <><path d="M3 12a9 9 0 109-9 9 9 0 00-8 5" /><path d="M3 4v4h4" /><path d="M12 8v4l3 2" /></>,
  upload: <><path d="M12 16V4" /><path d="M7 9l5-5 5 5" /><path d="M4 20h16" /></>,
  logout: <><path d="M15 12H4" /><path d="M9 8l-4 4 4 4" /><path d="M14 4h6v16h-6" /></>,
  menu: <><path d="M4 6h16" /><path d="M4 12h16" /><path d="M4 18h16" /></>,
  x: <><path d="M6 6l12 12" /><path d="M18 6L6 18" /></>,
  back: <><path d="M19 12H5" /><path d="M11 18l-6-6 6-6" /></>,
  download: <><path d="M12 4v12" /><path d="M7 11l5 5 5-5" /><path d="M4 20h16" /></>,
  rules: <><path d="M9 5h11" /><path d="M9 12h11" /><path d="M9 19h11" /><path d="M4 5l1 1 2-2" /><path d="M4 12l1 1 2-2" /><circle cx="5" cy="19" r="1.4" /></>,
  plug: <><path d="M9 2v6" /><path d="M15 2v6" /><path d="M7 8h10v3a5 5 0 01-10 0z" /><path d="M12 16v6" /></>,
  book: <><path d="M5 4h11a2 2 0 012 2v14H7a2 2 0 01-2-2z" /><path d="M5 18a2 2 0 012-2h11" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19" /></>,
  moon: <><path d="M20 14a8 8 0 11-9-11 6 6 0 009 11z" /></>,
  folder: <><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" /></>,
  folderPlus: <><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" /><path d="M12 11v4M10 13h4" /></>,
  trash: <><path d="M4 7h16" /><path d="M9 7V4h6v3" /><path d="M6 7l1 13h10l1-13" /></>,
  chevron: <><path d="M9 6l6 6-6 6" /></>,
  external: <><path d="M14 4h6v6" /><path d="M20 4l-9 9" /><path d="M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5" /></>,
  play: <><path d="M7 5l12 7-12 7z" /></>,
  sparkle: <><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" /></>,
  bell: <><path d="M6 9a6 6 0 1112 0c0 5 2 6 2 6H4s2-1 2-6z" /><path d="M10 20a2 2 0 004 0" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="M21 21l-4-4" /></>,
  globe: <><circle cx="12" cy="12" r="9" /><path d="M3 12h18" /><path d="M12 3c2.5 2.5 2.5 15 0 18" /><path d="M12 3c-2.5 2.5-2.5 15 0 18" /></>,
  logo: <><path d="M4 7l8-4 8 4v6c0 5-4 8-8 9-4-1-8-4-8-9z" /><path d="M9 12l2 2 4-4" /></>,
};

export function Icon({ name, size = 20, className, stroke = 1.7 }: { name: string; size?: number; className?: string; stroke?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {PATHS[name] ?? PATHS.file}
    </svg>
  );
}
