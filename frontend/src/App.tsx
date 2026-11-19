import { useCallback, useEffect, useRef, useState } from 'react'
import { api, post } from './lib/api'
import { taskError, taskStage } from './lib/task-status'
import type { Asset, DemoCase, Health, Page, Project, Review, Rewrite, Task } from './lib/types'
import Setup from './pages/Setup'
import ReviewPage from './pages/Review'
import ProjectPage from './pages/Project'
import Icon from './components/Icon'

const STORAGE = 'marketing-court-session-v1'

function savedSession(): { page?: Page; projectId?: string; reviewId?: string; taskId?: string } {
  try {
    return JSON.parse(localStorage.getItem(STORAGE) ?? '{}')
  } catch {
    return {}
  }
}

export default function App() {
  const initial = useRef(savedSession())
  const [page, setPage] = useState<Page>(
    ['review', 'project'].includes(initial.current.page ?? '') ? initial.current.page! : 'setup',
  )
  const [projectId, setProjectId] = useState(initial.current.projectId ?? '')
  const [health, setHealth] = useState<Health | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [examples, setExamples] = useState<DemoCase[]>([])
  const [history, setHistory] = useState<Review[] | null>(null)
  const [historyError, setHistoryError] = useState('')
  const [historyReload, setHistoryReload] = useState(0)
  const [review, setReview] = useState<Review | null>(null)
  const [asset, setAsset] = useState<Asset | null>(null)
  const [selectedRisk, setSelectedRisk] = useState('')
  const [rewrites, setRewrites] = useState<Rewrite[]>([])
  const [rechecks, setRechecks] = useState<Record<string, Review>>({})
  const [task, setTask] = useState<Task | null>(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [restored, setRestored] = useState(false)
  const refreshProjects = useCallback(
    async () => setProjects(await api<Project[]>('/api/projects')),
    [],
  )
  const loadReview = useCallback(async (id: string) => {
    const result = await api<Review>(`/api/reviews/${id}`)
    const [image, versions] = await Promise.all([
      api<Asset>(`/api/assets/${result.asset_version_id}`),
      api<Rewrite[]>(`/api/reviews/${id}/rewrites`),
    ])
    const checks = await Promise.all(
      versions.map((v) => api<Review>(`/api/reviews/${v.review_id}`)),
    )
    setReview(result)
    setProjectId(result.project_id)
    setAsset(image)
    setRewrites(versions)
    setRechecks(Object.fromEntries(checks.map((c) => [c.review_id, c])))
    setSelectedRisk(result.risks[0]?.risk_id ?? '')
  }, [])
  const action = async (label: string, fn: () => Promise<void>) => {
    setBusy(label)
    setError('')
    try {
      await fn()
    } catch (e) {
      setError(e instanceof Error ? e.message : '操作失败，请重试。')
    } finally {
      setBusy('')
    }
  }
  useEffect(() => {
    let cancelled = false
    async function restore() {
      try {
        const status = await api<Health>('/health')
        if (cancelled) return
        setHealth(status)
        await refreshProjects()
        setExamples(await api<DemoCase[]>('/api/demo-cases'))
        if (initial.current.page === 'review' && initial.current.reviewId)
          await loadReview(initial.current.reviewId)
        if (initial.current.taskId) {
          const task = await api<Task>(`/api/tasks/${initial.current.taskId}`)
          setTask(task)
          if (
            initial.current.page === 'review' &&
            task.kind === 'review' &&
            task.status === 'completed' &&
            task.result_id
          )
            await loadReview(task.result_id)
          else if (
            initial.current.page === 'review' &&
            task.kind === 'review' &&
            !initial.current.reviewId
          )
            setAsset(await api<Asset>(`/api/assets/${task.resource_id}`))
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : '恢复失败，请重新打开案例。')
      } finally {
        if (!cancelled) setRestored(true)
      }
    }
    void restore()
    return () => {
      cancelled = true
    }
  }, [refreshProjects, loadReview])
  useEffect(() => {
    if (restored)
      localStorage.setItem(
        STORAGE,
        JSON.stringify({
          page,
          projectId,
          reviewId: review?.review_id,
          taskId: task?.task_id,
        }),
      )
  }, [page, projectId, review, task, restored])
  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    setHistory(null)
    setHistoryError('')
    api<Review[]>(`/api/projects/${projectId}/reviews`)
      .then((items) => {
        if (!cancelled) setHistory(items)
      })
      .catch((e) => {
        if (!cancelled)
          setHistoryError(e instanceof Error ? e.message : '读取项目审核记录失败，请重试。')
      })
    return () => {
      cancelled = true
    }
  }, [projectId, review?.review_id, task?.status, historyReload])
  useEffect(() => {
    if (!task || !['queued', 'running'].includes(task.status)) return
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try {
        const current = await api<Task>(`/api/tasks/${task!.task_id}`)
        if (stopped) return
        setTask(current)
        if (current.status === 'completed' && current.result_id) {
          if (current.kind === 'review') await loadReview(current.result_id)
          else if (review) await loadReview(review.review_id)
          setPage('review')
          await refreshProjects()
        } else if (['queued', 'running'].includes(current.status)) timer = setTimeout(poll, 1000)
      } catch (e) {
        if (!stopped) {
          setError(e instanceof Error ? e.message : '读取进度失败')
          timer = setTimeout(poll, 3000)
        }
      }
    }
    timer = setTimeout(poll, 500)
    return () => {
      stopped = true
      clearTimeout(timer)
    }
  }, [task?.task_id, task?.status, review?.review_id, loadReview, refreshProjects])
  const pending = Boolean(task && ['queued', 'running'].includes(task.status))
  const locked = Boolean(busy) || pending
  const selectedProject = projects.find((p) => p.project_id === projectId)
  const openProject = (id: string) => {
    setProjectId(id)
    setHistoryReload((value) => value + 1)
    setPage('project')
    setError('')
  }
  const chooseReview = (id: string) =>
    action('读取审核版本', async () => {
      await loadReview(id)
      setTask(null)
      setPage('review')
    })
  return (
    <div className="app-layout">
      <a className="skip-link" href="#main-content">
        跳到主要内容
      </a>
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault()
            setProjectId('')
            setPage('setup')
          }}
        >
          <span className="brand-symbol">
            <Icon name="scales" size={27} />
          </span>
          <span className="brand-name">
            <strong>AI 营销审核</strong>
            <span>Marketing Court</span>
          </span>
        </a>
        <p className="sidebar-label">工作空间</p>
        <nav aria-label="主导航">
          <button
            aria-current={page === 'setup' && !projectId ? 'page' : undefined}
            onClick={() => {
              setProjectId('')
              setPage('setup')
            }}
          >
            <Icon name="folder" /> 项目与素材 <span className="nav-indicator" />
          </button>
          <div className="sidebar-project-heading">
            我的项目 <span>{projects.length}</span>
          </div>
          <div className="sidebar-project-list" aria-label="我的项目">
            {projects.map((project) => (
              <button
                key={project.project_id}
                className="sidebar-project"
                title={project.name}
                aria-current={projectId === project.project_id ? 'page' : undefined}
                disabled={locked}
                onClick={() => openProject(project.project_id)}
              >
                <Icon name="file" size={17} />
                <span className="sidebar-project-name">{project.name}</span>
                <span className="nav-indicator" />
              </button>
            ))}
            {projects.length === 0 && (
              <p className="sidebar-project-empty">创建项目后会显示在这里</p>
            )}
          </div>
        </nav>
        <a className="jury-link" href="/jury" aria-label="消费者模拟（独立页面）">
          <Icon name="spark" size={18} />
          <span>消费者模拟</span>
          <Icon name="external" size={14} />
        </a>
        <div className="workspace-note">
          <Icon name="shield" size={24} />
          <strong>让判断回到证据</strong>
          <p>定位广告宣称，追溯规则依据，对照改写与复核结果。</p>
        </div>
        <div className="sidebar-bottom">
          <div>
            <span className={`status-dot ${health ? 'online' : ''}`} />
            {health ? '本地服务已连接' : '连接本地服务中'}
          </div>
          <a href="/?ui=v1">
            查看第一版 <Icon name="external" size={13} />
          </a>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            <span>本地工作空间</span>
            <Icon name="chevron" size={13} />
            <strong>
              {selectedProject?.name ?? '项目与素材'}
              {page === 'review' ? ' / 审核报告' : ''}
            </strong>
          </div>
          <span className="mode-badge">
            <span className={`status-dot ${health ? 'online' : ''}`} />
            {health ? (health.mode === 'live' ? '实时模型' : '固定演示') : '等待连接'}
            {health && <span className="model-name">{health.model}</span>}
          </span>
        </header>
        <main id="main-content">
          {error && (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <button aria-label="关闭错误提示" onClick={() => setError('')}>
                ×
              </button>
            </div>
          )}
          {task && (
            <div
              className={`task-banner ${['failed', 'interrupted'].includes(task.status) ? 'failed' : ''}`}
              role="status"
            >
              <div>
                <strong>
                  {task.kind === 'review' ? '素材审核' : '改写复核'} · {taskStage(task.stage)}
                </strong>
                <p>
                  {taskError(task.error) ??
                    (task.status === 'completed'
                      ? '结果已保存。'
                      : '进度自动更新；连接短暂中断时会自动重试，最多尝试 3 次。可刷新页面恢复进度。')}
                </p>
              </div>
              {['failed', 'interrupted'].includes(task.status) ? (
                <button
                  disabled={!!busy}
                  onClick={() =>
                    void action('恢复任务', async () =>
                      setTask(await post<Task>(`/api/tasks/${task.task_id}/retry`)),
                    )
                  }
                >
                  重试此任务 ↗
                </button>
              ) : task.status === 'completed' ? (
                <button aria-label="关闭完成提示" onClick={() => setTask(null)}>
                  ×
                </button>
              ) : (
                <span className="spinner" />
              )}
            </div>
          )}
          {page === 'setup' && (
            <Setup
              health={health}
              projects={projects}
              examples={examples}
              key={projectId}
              initialProjectId={projectId}
              busy={locked}
              onExample={(id) =>
                void action('打开文案案例', async () => {
                  const r = await post<Review>(`/api/demo-cases/${id}`)
                  await loadReview(r.review_id)
                  await refreshProjects()
                  setTask(null)
                  setPage('review')
                })
              }
              onDemo={() =>
                void action('打开预设案例', async () => {
                  const r = await post<Review>('/api/demo')
                  await loadReview(r.review_id)
                  await refreshProjects()
                  setTask(null)
                  setPage('review')
                })
              }
              onUpload={(project, file, text, projectId) =>
                void action('上传素材', async () => {
                  const p = projectId
                    ? { project_id: projectId }
                    : await post<Project>('/api/projects', project)
                  const data = new FormData()
                  if (file) data.append('file', file)
                  if (text) data.append('text', text)
                  const a = await api<Asset>(`/api/projects/${p.project_id}/assets`, {
                    method: 'POST',
                    body: data,
                  })
                  setProjectId(p.project_id)
                  setAsset(a)
                  setReview(null)
                  setTask(null)
                  setRewrites([])
                  setPage('review')
                  setTask(await post<Task>(`/api/assets/${a.asset_version_id}/reviews`))
                  await refreshProjects()
                })
              }
            />
          )}
          {page === 'project' && selectedProject && (
            <ProjectPage
              project={selectedProject}
              history={history}
              error={historyError}
              onRetry={() => setHistoryReload((value) => value + 1)}
              busy={locked}
              onOpen={(id) => void chooseReview(id)}
              onAdd={() => setPage('setup')}
            />
          )}
          {page === 'review' && (
            <ReviewPage
              review={review}
              asset={asset}
              selectedRisk={selectedRisk}
              rewrites={rewrites}
              rechecks={rechecks}
              busy={locked}
              onSelect={setSelectedRisk}
              onSetup={() => setPage(selectedProject ? 'project' : 'setup')}
              onVersion={(id) => void chooseReview(id)}
              onRetryStart={() =>
                asset &&
                void action('启动审核', async () =>
                  setTask(await post<Task>(`/api/assets/${asset.asset_version_id}/reviews`)),
                )
              }
              onRewrite={(id) =>
                review &&
                void action('生成改写', async () =>
                  setTask(await post<Task>(`/api/reviews/${review.review_id}/risks/${id}/rewrite`)),
                )
              }
            />
          )}
        </main>
        <footer>
          <span>
            <Icon name="shield" size={14} />
            AI 辅助审核与消费者模拟，不构成法律意见或投放批准。
          </span>
          <a className="mobile-version-link" href="/?ui=v1">
            查看第一版
          </a>
          <span className="footer-wordmark">Marketing Court</span>
        </footer>
      </div>
    </div>
  )
}
