import { useState } from 'react'
import { pages, type PageKey } from './pages'

export default function App() {
  const [active, setActive] = useState<PageKey>('setup')
  const Page = pages[active]

  return (
    <main className="shell">
      <header>
        <p className="eyebrow">项目骨架 · 业务功能待开发</p>
        <h1>AI Marketing Court</h1>
        <p>证据驱动的营销素材审核与复核</p>
      </header>
      <nav aria-label="页面导航">
        {Object.entries(pages).map(([key, entry]) => (
          <button key={key} type="button" aria-current={active === key ? 'page' : undefined} onClick={() => setActive(key as PageKey)}>
            {entry.label}
          </button>
        ))}
      </nav>
      <Page.component />
      <footer>AI 辅助审核不构成法律意见；模拟消费者输出不代表真实市场调查。</footer>
    </main>
  )
}
