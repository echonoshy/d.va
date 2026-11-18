import type { CSSProperties } from 'react';

const paths = {
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
export function Icon({ name, size = 18 }: { name: keyof typeof paths; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}

export function Meter({ small = false }) {
  return (
    <span aria-hidden="true" className={'meter' + (small ? ' meter-small' : '')}>
      {[9, 18, 26, 20, 13].map((h) => {
        const style: CSSProperties & { '--h': number } = { '--h': h };
        return <i key={h} style={style} />;
      })}
    </span>
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
