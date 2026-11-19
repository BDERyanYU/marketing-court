import Setup from './Setup'
import Review from './Review'
import Jury from './Jury'
import Compare from './Compare'

export const pages = {
  setup: { label: '项目设置', component: Setup },
  review: { label: '审核工作台', component: Review },
  jury: { label: '数字人像测试', component: Jury },
  compare: { label: '对比与导出', component: Compare },
} as const

export type PageKey = keyof typeof pages
