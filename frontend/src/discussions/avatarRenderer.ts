import { avatarGeometry, dot, type Vector } from './avatarGeometry'

interface ScreenPoint {
  x: number
  y: number
  depth: number
}

const radians = Math.PI / 180
const images = new Map<string, ImageData>()
const light: Vector = [-0.24, 0.45, 0.86]

function camera(yaw: number) {
  const angle = yaw * radians
  const tilt = 8 * radians
  const sinYaw = Math.sin(angle)
  const cosYaw = Math.cos(angle)
  const sinTilt = Math.sin(tilt)
  const cosTilt = Math.cos(tilt)
  return ([x, y, z]: Vector): Vector => {
    const depth = z * cosYaw - x * sinYaw
    return [x * cosYaw + z * sinYaw, y * cosTilt - depth * sinTilt, y * sinTilt + depth * cosTilt]
  }
}

function edge(a: ScreenPoint, b: ScreenPoint, x: number, y: number) {
  return (b.x - a.x) * (y - a.y) - (b.y - a.y) * (x - a.x)
}

// The depth buffer compares surfaces per pixel, including intersecting geometry.
function triangle(
  output: ImageData,
  depths: Float32Array,
  a: ScreenPoint,
  b: ScreenPoint,
  c: ScreenPoint,
  rgb: Vector,
) {
  const { width, height, data } = output
  const area = edge(a, b, c.x, c.y)
  if (Math.abs(area) < 0.001) return
  const minX = Math.max(0, Math.floor(Math.min(a.x, b.x, c.x)))
  const maxX = Math.min(width - 1, Math.ceil(Math.max(a.x, b.x, c.x)))
  const minY = Math.max(0, Math.floor(Math.min(a.y, b.y, c.y)))
  const maxY = Math.min(height - 1, Math.ceil(Math.max(a.y, b.y, c.y)))

  for (let y = minY; y <= maxY; y++) {
    for (let x = minX; x <= maxX; x++) {
      const wa = edge(b, c, x + 0.5, y + 0.5) / area
      const wb = edge(c, a, x + 0.5, y + 0.5) / area
      const wc = 1 - wa - wb
      if (wa < 0 || wb < 0 || wc < 0) continue

      const depth = wa * a.depth + wb * b.depth + wc * c.depth
      const pixel = y * width + x
      if (depth <= depths[pixel]) continue

      depths[pixel] = depth
      const offset = pixel * 4
      data[offset] = rgb[0]
      data[offset + 1] = rgb[1]
      data[offset + 2] = rgb[2]
      data[offset + 3] = 255
    }
  }
}

export function renderAvatar(index: number, yaw: number, size: number) {
  const key = `${index}:${yaw}:${size}`
  const existing = images.get(key)
  if (existing) return existing

  const output = new ImageData(size, size)
  const depths = new Float32Array(size * size).fill(-Infinity)
  const rotate = camera(yaw)
  const scale = size * 0.407

  function project(point: Vector): ScreenPoint {
    const [x, y, depth] = rotate(point)
    return { x: size / 2 + x * scale, y: size * 0.962 - y * scale, depth }
  }

  for (const surface of avatarGeometry(index)) {
    const normal = rotate(surface.normal)
    if (normal[2] <= 0) continue
    const intensity = 0.66 + Math.max(0, dot(normal, light)) * 0.4
    const rgb: Vector = [
      surface.color[0] * intensity,
      surface.color[1] * intensity,
      surface.color[2] * intensity,
    ]
    const points = surface.points.map(project)
    for (let i = 1; i < points.length - 1; i++) {
      triangle(output, depths, points[0], points[i], points[i + 1], rgb)
    }
  }

  if (images.size >= 40) {
    const first = images.keys().next().value
    if (first !== undefined) images.delete(first)
  }
  images.set(key, output)
  return output
}
