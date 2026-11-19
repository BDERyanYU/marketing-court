import type { CSSProperties, ReactNode } from 'react'

export type IconName =
  | 'scales'
  | 'folder'
  | 'scan'
  | 'upload'
  | 'arrow'
  | 'external'
  | 'check'
  | 'file'
  | 'shield'
  | 'clock'
  | 'download'
  | 'chevron'
  | 'spark'
  | 'back'

const paths: Record<IconName, ReactNode> = {
  scales: (
    <>
      <path d="M12 3v17M5 21h14M5 7h14M12 3l-2 4M12 3l2 4M5 7l-4 7h8L5 7Zm14 0-4 7h8l-4-7Z" />
      <path d="M1 14a4 4 0 0 0 8 0m6 0a4 4 0 0 0 8 0" />
    </>
  ),
  folder: (
    <path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Zm0 2h18" />
  ),
  scan: (
    <>
      <path d="M8 3H4a1 1 0 0 0-1 1v4m13-5h4a1 1 0 0 1 1 1v4M3 16v4a1 1 0 0 0 1 1h4m8 0h4a1 1 0 0 0 1-1v-4M1 12h22M8 8h8M8 16h5" />
    </>
  ),
  upload: <path d="M12 16V3m-5 5 5-5 5 5M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5" />,
  arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
  external: (
    <path d="M14 3h7v7m0-7L10 14m-1-9H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4" />
  ),
  check: <path d="m5 12 4 4L19 6" />,
  file: (
    <>
      <path d="M14 2H5a1 1 0 0 0-1 1v18a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V8l-6-6Zm0 0v6h6M8 13h8M8 17h5" />
    </>
  ),
  shield: <path d="m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6l9-4Zm-4 9 3 3 5-6" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  download: <path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4" />,
  chevron: <path d="m9 5 7 7-7 7" />,
  spark: <path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3ZM20 2v4m-2-2h4" />,
  back: <path d="M20 12H4m6-6-6 6 6 6" />,
}

export default function Icon({
  name,
  size = 20,
  style,
}: {
  name: IconName
  size?: number
  style?: CSSProperties
}) {
  return (
    <svg
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={style}
    >
      {paths[name]}
    </svg>
  )
}
