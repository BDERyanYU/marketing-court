export type Vector = readonly [number, number, number]

export interface Face {
  points: Vector[]
  normal: Vector
  color: Vector
}

interface Section {
  y: number
  halfWidth: number
  halfDepth: number
  bevel: number
  x?: number
  z?: number
}

const jackets = [
  '#805082',
  '#9b637d',
  '#786499',
  '#a4606e',
  '#4b7468',
  '#70915e',
  '#577c50',
  '#8b9d58',
  '#b78236',
  '#bc6b45',
  '#c8952f',
  '#a86e36',
  '#356c75',
  '#467a91',
  '#596789',
  '#466680',
]
const skinTones = ['#edbc9a', '#c58b62', '#a97152', '#e1a878', '#946447']
const hairTones = ['#352b39', '#5c413b', '#aa7852', '#70747a', '#382e2c', '#8b6447']
const frames = new Set([1, 4, 7, 9, 10, 13])
const models = new Map<number, Face[]>()

const subtract = (a: Vector, b: Vector): Vector => [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
export const dot = (a: Vector, b: Vector) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

function normalTo(points: Vector[]): Vector {
  const a = subtract(points[1], points[0])
  const b = subtract(points[2], points[0])
  const cross: Vector = [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ]
  const length = Math.hypot(...cross)
  return length ? [cross[0] / length, cross[1] / length, cross[2] / length] : [0, 0, 0]
}

function palette(hex: string): Vector {
  return [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16)) as unknown as Vector
}

function tint(color: Vector, factor: number): Vector {
  return [color[0] * factor, color[1] * factor, color[2] * factor]
}

function centerOf(points: Vector[]): Vector {
  const result = [0, 0, 0]
  for (const point of points) {
    result[0] += point[0]
    result[1] += point[1]
    result[2] += point[2]
  }
  return [result[0] / points.length, result[1] / points.length, result[2] / points.length]
}

function face(mesh: Face[], points: Vector[], color: Vector, interior?: Vector) {
  const normal = normalTo(points)
  const outside = interior ? subtract(centerOf(points), interior) : ([0, 0, 1] as const)
  if (dot(normal, outside) < 0) {
    mesh.push({
      points: [...points].reverse(),
      normal: [-normal[0], -normal[1], -normal[2]],
      color,
    })
  } else {
    mesh.push({ points, normal, color })
  }
}

function ring({ y, halfWidth: w, halfDepth: d, bevel: b, x = 0, z = 0 }: Section): Vector[] {
  return [
    [x - w + b, y, z + d],
    [x + w - b, y, z + d],
    [x + w, y, z + d - b],
    [x + w, y, z - d + b],
    [x + w - b, y, z - d],
    [x - w + b, y, z - d],
    [x - w, y, z - d + b],
    [x - w, y, z + d - b],
  ]
}

function section(
  y: number,
  halfWidth: number,
  halfDepth: number,
  bevel: number,
  x = 0,
  z = 0,
): Section {
  return { y, halfWidth, halfDepth, bevel, x, z }
}

function bevelled(mesh: Face[], sections: Section[], color: Vector) {
  const rings = sections.map(ring)
  const interior = centerOf(rings.flat())
  face(mesh, rings[0], tint(color, 0.9), interior)
  face(mesh, rings[rings.length - 1], tint(color, 1.09), interior)
  for (let row = 0; row < rings.length - 1; row++) {
    for (let side = 0; side < 8; side++) {
      const next = (side + 1) % 8
      face(
        mesh,
        [rings[row][side], rings[row][next], rings[row + 1][next], rings[row + 1][side]],
        tint(color, side % 2 ? 0.89 : 1),
        interior,
      )
    }
  }
}

function block(mesh: Face[], at: Vector, size: Vector, color: Vector, corner = 0.02) {
  const [x, y, z] = at
  const [width, height, depth] = size
  const bevel = Math.min(corner, width / 4, depth / 4)
  bevelled(
    mesh,
    [
      section(y - height / 2, width / 2, depth / 2, bevel, x, z),
      section(y + height / 2, width / 2, depth / 2, bevel, x, z),
    ],
    color,
  )
}

function eye(mesh: Face[], x: number, color: Vector) {
  const points: Vector[] = []
  for (let side = 0; side < 8; side++) {
    const angle = (side / 8) * 2 * Math.PI
    points.push([x + Math.cos(angle) * 0.041, 1.51 + Math.sin(angle) * 0.047, 0.376])
  }
  face(mesh, points, color)
}

function nose(mesh: Face[], skin: Vector) {
  const vertices: Vector[] = [
    [-0.067, 1.56, 0.355],
    [0.067, 1.56, 0.355],
    [-0.095, 1.35, 0.364],
    [0.095, 1.35, 0.364],
    [0, 1.36, 0.536],
  ]
  const interior = centerOf(vertices)
  const [bridgeLeft, bridgeRight, baseLeft, baseRight, tip] = vertices
  face(mesh, [bridgeLeft, bridgeRight, tip], tint(skin, 1.08), interior)
  face(mesh, [bridgeLeft, tip, baseLeft], skin, interior)
  face(mesh, [bridgeRight, baseRight, tip], tint(skin, 0.95), interior)
  face(mesh, [tip, baseRight, baseLeft], tint(skin, 0.82), interior)
}

function glasses(mesh: Face[], color: Vector) {
  for (const side of [-1, 1]) {
    const x = side * 0.185
    block(mesh, [x, 1.595, 0.4], [0.269, 0.035, 0.035], color)
    block(mesh, [x, 1.425, 0.4], [0.269, 0.029, 0.035], color)
    for (const edge of [-1, 1]) {
      block(mesh, [x + edge * 0.119, 1.51, 0.4], [0.031, 0.18, 0.036], color)
    }
    block(mesh, [side * 0.322, 1.57, 0.245], [0.031, 0.035, 0.3], color)
  }
  block(mesh, [0, 1.535, 0.405], [0.106, 0.031, 0.036], color)
}

function createModel(index: number): Face[] {
  const mesh: Face[] = []
  const jacket = palette(jackets[index])
  const skin = palette(skinTones[(index * 3) % skinTones.length])
  const hair = palette(hairTones[(index + Math.floor(index / 4)) % hairTones.length])
  const ink = palette('#28222c')
  const shirt = palette(index % 3 === 0 ? '#dac7a5' : '#dcd7cb')

  bevelled(
    mesh,
    [
      section(0.05, 0.66, 0.31, 0.14, 0, -0.02),
      section(0.54, 0.72, 0.32, 0.15, 0, -0.03),
      section(0.75, 0.58, 0.27, 0.13, 0, -0.04),
      section(0.88, 0.27, 0.16, 0.06, 0, -0.025),
    ],
    jacket,
  )
  block(mesh, [0, 0.93, 0], [0.31, 0.36, 0.33], tint(skin, 0.82), 0.056)
  face(
    mesh,
    [
      [-0.26, 0.804, 0.273],
      [0.26, 0.804, 0.273],
      [0.16, 0.61, 0.313],
      [0, 0.27, 0.315],
      [-0.16, 0.61, 0.313],
    ],
    shirt,
  )
  for (const side of [-1, 1]) {
    face(
      mesh,
      [
        [side * 0.27, 0.805, 0.278],
        [side * 0.44, 0.657, 0.301],
        [side * 0.28, 0.469, 0.324],
        [side * 0.34, 0.273, 0.326],
        [side * 0.093, 0.589, 0.324],
      ],
      tint(jacket, 1.19),
    )
    block(mesh, [side * 0.54, 0.16, 0.237], [0.3, 0.22, 0.24], tint(jacket, 0.8), 0.07)
  }
  block(mesh, [index % 2 ? -0.32 : 0.32, 0.173, 0.377], [0.22, 0.15, 0.18], tint(skin, 0.93), 0.035)

  const width = [0.405, 0.365, 0.42][index % 3]
  bevelled(
    mesh,
    [
      section(1.02, width * 0.59, 0.205, 0.078, 0, 0.015),
      section(1.15, width * 0.92, 0.311, 0.095, 0, 0.018),
      section(1.67, width, 0.342, 0.089, 0, 0.025),
      section(1.86, width * 0.94, 0.29, 0.062),
      section(1.955, width * 0.73, 0.24, 0.052),
    ],
    skin,
  )
  for (const side of [-1, 1]) {
    block(
      mesh,
      [side * (width + 0.014), 1.404, -0.05],
      [0.147, 0.228, 0.16],
      tint(skin, 0.92),
      0.044,
    )
    eye(mesh, side * 0.158, ink)
    face(
      mesh,
      [
        [side * 0.09, 1.637, 0.375],
        [side * 0.23, 1.66, 0.375],
        [side * 0.24, 1.624, 0.375],
        [side * 0.095, 1.601, 0.375],
      ],
      tint(hair, 0.76),
    )
  }
  nose(mesh, skin)
  if (index % 4 === 1) {
    face(
      mesh,
      [
        [-0.228, 1.23, 0.345],
        [0.228, 1.245, 0.345],
        [0.174, 1.105, 0.334],
        [-0.152, 1.065, 0.334],
      ],
      tint(hair, 1.04),
    )
  }
  face(
    mesh,
    [
      [-0.118, 1.266, 0.365],
      [0.115, 1.278, 0.365],
      [0.018, 1.211, 0.365],
    ],
    palette('#713d37'),
  )
  if (frames.has(index)) glasses(mesh, tint(ink, 1.6))

  const hairstyle = index % 4
  const sweep = index % 2 ? 0.055 : -0.055
  bevelled(
    mesh,
    [
      section(1.705, width + 0.026, 0.317, 0.091, 0, -0.018),
      section(1.87, width + 0.073, 0.363, 0.112, sweep / 2, -0.016),
      section(2.068 + (hairstyle === 2 ? 0.055 : 0), width * 0.93, 0.303, 0.115, sweep, -0.03),
      section(2.14 + (hairstyle === 2 ? 0.06 : 0), width * 0.58, 0.198, 0.072, sweep * 1.4, -0.045),
    ],
    hair,
  )
  face(
    mesh,
    [
      [sweep - 0.306, 1.912, 0.357],
      [sweep + 0.288, 1.898, 0.357],
      [sweep + 0.105, 1.76, 0.357],
      [sweep - 0.18, 1.669, 0.318],
    ],
    tint(hair, 1.24),
  )

  if (hairstyle === 0 || hairstyle === 3) {
    bevelled(
      mesh,
      [
        section(hairstyle === 0 ? 1.095 : 1.247, width + 0.01, 0.19, 0.07, 0, -0.263),
        section(1.729, width + 0.068, 0.255, 0.085, 0, -0.192),
      ],
      tint(hair, 0.88),
    )
    for (const side of [-1, 1]) {
      block(mesh, [side * (width + 0.013), 1.5, -0.122], [0.15, 0.564, 0.31], hair, 0.064)
    }
  }
  if (hairstyle === 3) {
    bevelled(
      mesh,
      [
        section(1.998, 0.15, 0.15, 0.047, 0.12, -0.191),
        section(2.249, 0.193, 0.181, 0.077, 0.105, -0.218),
        section(2.311, 0.106, 0.108, 0.046, 0.085, -0.233),
      ],
      tint(hair, 1.13),
    )
  }
  return mesh
}

export function avatarGeometry(index: number): Face[] {
  const key = index % jackets.length
  const saved = models.get(key)
  if (saved) return saved
  const model = createModel(key)
  models.set(key, model)
  return model
}
