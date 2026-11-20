import { useEffect, useRef } from 'react'
import { renderAvatar } from './avatarRenderer'

const sizes = { small: 96, table: 320, preview: 240 }

export default function Portrait({
  index,
  yaw = 0,
  size = 'small',
}: {
  index?: number
  yaw?: number
  size?: keyof typeof sizes
}) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const pixels = sizes[size]

  useEffect(() => {
    if (index === undefined) return
    const context = canvas.current?.getContext('2d')
    if (context) context.putImageData(renderAvatar(index, yaw, pixels), 0, 0)
  }, [index, yaw, pixels])

  if (index === undefined)
    return <span className="rt-portrait rt-portrait-empty" aria-hidden="true" />
  return (
    <canvas
      ref={canvas}
      width={pixels}
      height={pixels}
      data-yaw={yaw}
      className="rt-portrait"
      aria-hidden="true"
    />
  )
}
