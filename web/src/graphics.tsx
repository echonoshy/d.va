const paths = {
  podcast: (
    <>
      <rect x="8" y="2.5" width="8" height="13" rx="4" />
      <path d="M5 10a7 7 0 0 0 14 0M12 17v4.5M8.5 21.5h7" />
    </>
  ),
  text: (
    <>
      <path d="M3 5h12M3 9h8M3 13h5M13 12v6m3-9v12m3-8v4m3-6v8" />
    </>
  ),
  code: (
    <>
      <path d="m7.5 7-5 5 5 5m9-10 5 5-5 5M14 4l-4 16" />
    </>
  ),
  voices: (
    <>
      <path d="M2.5 19v-2a5 5 0 0 1 10 0v2M15 12a5 5 0 0 1 6 5v2" />
      <circle cx="7.5" cy="7" r="3" />
      <path d="M15 4a3 3 0 0 1 0 6" />
    </>
  ),
  clone: (
    <>
      <rect x="3" y="7" width="12" height="14" rx="3" />
      <path d="M9 7V5a2 2 0 0 1 2-2h7a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3M6 14h1.5l1-2 1.5 4 1-2h1" />
    </>
  ),
  train: (
    <>
      <rect x="6" y="6" width="12" height="12" rx="2" />
      <path d="M9 3v3m6-3v3M9 18v3m6-3v3M3 9h3m-3 6h3m12-6h3m-3 6h3" />
      <path d="M10 10h4v4h-4z" />
    </>
  ),
  chat: (
    <>
      <path d="M20.5 11A8.5 7.5 0 0 1 12 18.5a10 10 0 0 1-3-.5L4 20l.7-4A7 7 0 0 1 3.5 11a8.5 7.5 0 0 1 17 0Z" />
      <path d="M8 11h.01m4 0h.01m4 0h.01" strokeWidth="3" />
    </>
  ),
  system: (
    <>
      <rect x="2.5" y="4" width="19" height="13" rx="2" />
      <path d="M8 21h8m-4-4v4m-6-9 2.5 0 1.5-2 2.5 4 1.5-2H18" />
    </>
  ),
  help: (
    <>
      <path d="M12 5v15M3 4.5c4-1 7 0 9 1.5 2-1.5 5-2.5 9-1.5v14c-4-1-7-.5-9 1.5-2-2-5-2.5-9-1.5Z" />
    </>
  ),
  script: (
    <>
      <path d="M15 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path d="M14 3v6h6M8 13h8m-8 4h5" />
    </>
  ),
  arrow: <path d="M4 12h15m-6-6 6 6-6 6" />,
  menu: <path d="M3.5 6h17m-17 6h17m-17 6h17" />,
  play: <path d="m7 4.5 12 7.5-12 7.5z" fill="currentColor" strokeLinejoin="round" />,
  layers: (
    <>
      <path d="m3 8 9-5 9 5-9 5zM3 12l9 5 9-5M3 16l9 5 9-5" />
    </>
  ),
  headphones: (
    <>
      <path d="M3 14v-2a9 9 0 0 1 18 0v2" />
      <rect x="3" y="12" width="4.5" height="8" rx="1.7" />
      <rect x="16.5" y="12" width="4.5" height="8" rx="1.7" />
    </>
  ),
  tune: (
    <>
      <path d="M3 7h7m4 0h7M3 17h2m4 0h12" />
      <circle cx="12" cy="7" r="2.5" />
      <circle cx="7" cy="17" r="2.5" />
    </>
  ),
  upload: (
    <>
      <path d="M7 18H5a4 4 0 0 1-.6-8 7 7 0 0 1 13.3-1.5A4.8 4.8 0 0 1 19 18h-2" />
      <path d="M12 20V12m-3 3 3-3 3 3" />
    </>
  ),
  chevron: <path d="m7 10 5 5 5-5" />,
  add: <path d="M12 5v14M5 12h14" />,
  trash: (
    <>
      <path d="M4 6.5h16M9.5 3.5h5M7 7l.6 12.6a1.5 1.5 0 0 0 1.5 1.4h5.8a1.5 1.5 0 0 0 1.5-1.4L17 7M10 10v7m4-7v7" />
    </>
  ),
  spark: (
    <path d="M12 2.5c1.1 5.7 3.2 8 9.2 9.5-6 1.5-8.1 3.8-9.2 9.5-1.2-5.7-3.2-8-9.2-9.5 6-1.5 8-3.8 9.2-9.5Z" />
  ),
  download: (
    <>
      <path d="M12 3v12m-4-4 4 4 4-4M4 16v3a1.5 1.5 0 0 0 1.5 1.5h13a1.5 1.5 0 0 0 1.5-1.5v-3" />
    </>
  ),
  close: <path d="m6 6 12 12M18 6 6 18" />,
};
export type IconName = keyof typeof paths;
export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.85"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}

export function Wave() {
  const heights = [
    3, 5, 7, 6, 5, 10, 14, 24, 16, 9, 7, 12, 21, 31, 17, 10, 6, 8, 12, 18, 10, 7, 5, 6, 4, 5, 3, 4,
  ];
  return (
    <span className="wave" aria-hidden="true">
      {heights.map((h, i) => (
        <i key={i} style={{ height: h }} />
      ))}
    </span>
  );
}
