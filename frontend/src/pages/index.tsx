import Setup from './Setup'
import Review from './Review'
import Court from './Court'
import Jury from './Jury'
import Compare from './Compare'

export const pages = {
  setup: { label: '项目设置', component: Setup },
  review: { label: '审核工作台', component: Review },
  court: { label: '模拟法庭', component: Court },
  jury: { label: '消费者陪审团', component: Jury },
  compare: { label: '对比与导出', component: Compare },
} as const

export type PageKey = keyof typeof pages
