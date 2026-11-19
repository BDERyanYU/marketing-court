export default function BottleArt() {
  return (
    <svg className="bottle-art" viewBox="0 0 400 350" fill="none" aria-hidden="true">
      <defs>
        <linearGradient
          id="bottle-body"
          x1="160"
          y1="160"
          x2="282"
          y2="160"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#7d9ca3" />
          <stop offset=".16" stopColor="#c3d7d8" />
          <stop offset=".42" stopColor="#a5c3c7" />
          <stop offset=".8" stopColor="#71979e" />
          <stop offset="1" stopColor="#527b85" />
        </linearGradient>
        <linearGradient
          id="bottle-lid"
          x1="172"
          y1="50"
          x2="252"
          y2="50"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#244655" />
          <stop offset=".4" stopColor="#3e6471" />
          <stop offset="1" stopColor="#173b4b" />
        </linearGradient>
        <linearGradient
          id="bottle-light"
          x1="160"
          y1="110"
          x2="260"
          y2="270"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="white" stopOpacity=".22" />
          <stop offset="1" stopColor="white" stopOpacity="0" />
        </linearGradient>
        <radialGradient id="bottle-shadow">
          <stop stopColor="#264d60" stopOpacity=".2" />
          <stop offset="1" stopColor="#264d60" stopOpacity="0" />
        </radialGradient>
      </defs>
      <ellipse cx="226" cy="310" rx="134" ry="25" fill="url(#bottle-shadow)" />
      <circle cx="204" cy="171" r="133" stroke="#afc8d5" strokeOpacity=".5" />
      <circle cx="204" cy="171" r="111" stroke="#afc8d5" strokeOpacity=".3" strokeDasharray="2 8" />
      <path d="M80 275h246" stroke="#b4cbd7" strokeOpacity=".5" />
      <g transform="rotate(11 215 180)">
        <path
          d="M184 63v23c0 8-22 18-22 40v151c0 19 12 28 29 28h47c17 0 29-9 29-28V126c0-22-22-32-22-40V63h-61Z"
          fill="url(#bottle-body)"
          stroke="#668d96"
        />
        <path
          d="M185 78h59v13c0 6 15 18 18 29h-95c3-11 18-23 18-29V78Z"
          fill="url(#bottle-light)"
        />
        <path
          d="M175 128v145c0 14 5 20 13 22"
          stroke="#e2efed"
          strokeOpacity=".5"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <rect x="182" y="48" width="65" height="33" rx="7" fill="url(#bottle-lid)" />
        <path d="M186 56h57m-57 6h57m-57 6h57" stroke="#a1bec5" strokeOpacity=".2" />
        <path d="M200 48v-9a14 14 0 0 1 28 0v9" stroke="#315360" strokeWidth="7" />
        <path
          d="M194 191c13-3 28-3 41 0m-32 12c7-2 15-2 23 0"
          stroke="#355d66"
          strokeOpacity=".8"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        <text
          x="215"
          y="222"
          textAnchor="middle"
          fontFamily="Georgia, serif"
          fontSize="10"
          letterSpacing="3"
          fill="#355d66"
        >
          COURT
        </text>
        <path d="M171 286c24 7 62 7 88 0" stroke="#4e7681" strokeOpacity=".4" />
      </g>
      <g transform="translate(18 135) rotate(-5)">
        <rect width="169" height="87" rx="5" fill="white" stroke="#dae4eb" />
        <path d="M0 5a5 5 0 0 1 5-5h3v87H5a5 5 0 0 1-5-5V5Z" fill="#b48156" />
        <text x="22" y="32" fill="#687b8b" fontSize="11" fontFamily="Microsoft YaHei, sans-serif">
          待核查的广告宣称
        </text>
        <text x="22" y="58" fill="#243e55" fontSize="20" fontFamily="Georgia, serif">
          100% Eco-Friendly
        </text>
      </g>
    </svg>
  )
}
