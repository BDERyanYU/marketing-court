import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { api, post } from './lib/api'
import { taskError, taskStage } from './lib/task-status'
import type { Asset, DemoCase, Health, Page, Project, Review, Rewrite, Task } from './lib/types'
import Setup from './pages/Setup'
import ReviewPage from './pages/Review'
import ProjectPage from './pages/Project'
import Jury from './pages/Jury'
import Icon from './components/Icon'
import type { DiscussionTarget } from './discussions/types'
import './persona.css'

const STORAGE = 'marketing-court-session-v1'
const Roundtable = lazy(() => import('./discussions/Roundtable'))

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
    location.pathname.replace(/\/$/, '') === '/jury'
      ? 'persona'
      : location.hash === '#greenlint-cases'
        ? 'setup'
        : ['review', 'project'].includes(initial.current.page ?? '')
          ? initial.current.page!
          : 'setup',
  )
  const [personaVisited, setPersonaVisited] = useState(
    location.pathname.replace(/\/$/, '') === '/jury',
  )
  const [personaHealth, setPersonaHealth] = useState<Health | null>(null)
  const navigate = useCallback((next: Page) => {
    setPage(next)
    if (next === 'persona') {
      setPersonaVisited(true)
      if (location.pathname.replace(/\/$/, '') !== '/jury') {
        const saved = sessionStorage.getItem('marketing-persona-record')
        window.history.pushState(null, '', saved?.startsWith('/jury?') ? saved : '/jury')
      }
    } else if (location.pathname.replace(/\/$/, '') === '/jury')
      window.history.pushState(null, '', '/review')
  }, [])
  useEffect(() => {
    const sync = () => {
      const isPersona = location.pathname.replace(/\/$/, '') === '/jury'
      if (isPersona) setPersonaVisited(true)
      setPage(isPersona ? 'persona' : 'setup')
    }
    addEventListener('popstate', sync)
    return () => removeEventListener('popstate', sync)
  }, [])
  const [projectId, setProjectId] = useState(initial.current.projectId ?? '')
  const [health, setHealth] = useState<Health | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [examples, setExamples] = useState<DemoCase[]>([])
  const [history, setHistory] = useState<Review[] | null>(null)
  const [historyError, setHistoryError] = useState('')
  const [historyReload, setHistoryReload] = useState(0)
  const [review, setReview] = useState<Review | null>(null)
  const [roundtable, setRoundtable] = useState<DiscussionTarget | null>(null)
  const [asset, setAsset] = useState<Asset | null>(null)
  const [selectedRisk, setSelectedRisk] = useState('')
  const [rewrites, setRewrites] = useState<Rewrite[]>([])
  const [rechecks, setRechecks] = useState<Record<string, Review>>({})
  const [task, setTask] = useState<Task | null>(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [renamingProject, setRenamingProject] = useState<Project | null>(null)
  const [renameName, setRenameName] = useState('')
  const [renameError, setRenameError] = useState('')
  const [renameBusy, setRenameBusy] = useState(false)
  const renameDialog = useRef<HTMLDialogElement>(null)
  const [progressDismissed, setProgressDismissed] = useState(false)
  useEffect(() => {
    if (renamingProject) renameDialog.current?.showModal()
    else renameDialog.current?.close()
  }, [renamingProject])
  useEffect(() => setProgressDismissed(false), [task?.task_id, task?.status])
  const [deletingProject, setDeletingProject] = useState<Project | null>(null)
  const [deleteError, setDeleteError] = useState('')
  const [deleteBusy, setDeleteBusy] = useState(false)
  const deleteDialog = useRef<HTMLDialogElement>(null)
  const deleteTrigger = useRef<HTMLButtonElement | null>(null)
  useEffect(() => {
    if (deletingProject) deleteDialog.current?.showModal()
    else if (deleteDialog.current?.open) {
      deleteDialog.current.close()
      if (deleteTrigger.current?.isConnected) deleteTrigger.current.focus()
    }
  }, [deletingProject])
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
          if (location.pathname.replace(/\/$/, '') !== '/jury') navigate('review')
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
  const showProgress =
    page !== 'persona' &&
    (pending ||
      busy === '上传素材' ||
      busy === '启动审核' ||
      busy === '生成改写' ||
      busy === '恢复任务')
  const saveProjectName = async () => {
    if (!renamingProject || renameBusy) return
    setRenameBusy(true)
    setRenameError('')
    try {
      const updated = await api<Project>(`/api/projects/${renamingProject.project_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: renameName.trim() }),
      })
      setProjects((items) => items.map((p) => (p.project_id === updated.project_id ? updated : p)))
      setRenamingProject(null)
    } catch (e) {
      setRenameError(e instanceof Error ? e.message : '重命名失败，请重试。')
    } finally {
      setRenameBusy(false)
    }
  }
  const visibleHealth = page === 'persona' ? personaHealth : health
  const selectedProject = projects.find((p) => p.project_id === projectId)
  const openProject = (id: string) => {
    setProjectId(id)
    setHistoryReload((value) => value + 1)
    navigate('project')
    setError('')
  }
  const chooseReview = (id: string) =>
    action('读取审核版本', async () => {
      await loadReview(id)
      setTask(null)
      navigate('review')
    })
  const confirmDelete = async () => {
    if (!deletingProject || deleteBusy) return
    setDeleteBusy(true)
    setDeleteError('')
    try {
      const id = deletingProject.project_id
      const result = await api<{ file_cleanup_pending: boolean }>(`/api/projects/${id}`, {
        method: 'DELETE',
      })
      setProjects((items) => items.filter((p) => p.project_id !== id))
      if (review?.project_id === id || asset?.project_id === id) {
        setReview(null)
        setAsset(null)
        setRewrites([])
        setRechecks({})
        setSelectedRisk('')
        setTask(null)
      }
      if (projectId === id) {
        setProjectId('')
        setHistory(null)
        setHistoryError('')
        if (page !== 'persona') navigate('setup')
      }
      setError(
        result.file_cleanup_pending
          ? '项目已删除，部分原图文件未能清理，请检查文件是否被占用。'
          : '',
      )
      setDeletingProject(null)
    } catch (e) {
      setDeleteError(e instanceof Error ? e.message : '删除失败，请重试。')
    } finally {
      setDeleteBusy(false)
    }
  }
  return (
    <div className="app-layout">
      <a className="skip-link" href="#main-content">
        跳到主要内容
      </a>
      <aside className="sidebar">
        <a className="brand" href="/">
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
              navigate('setup')
            }}
          >
            <Icon name="folder" /> 项目与素材 <span className="nav-indicator" />
          </button>
          <button
            aria-current={page === 'persona' ? 'page' : undefined}
            onClick={() => navigate('persona')}
          >
            <Icon name="spark" /> 数字人像测试 <span className="nav-indicator" />
          </button>
          <button type="button" onClick={() => setRoundtable('standalone')}>
            <Icon name="scales" /> 圆桌讨论 <span className="nav-indicator" />
          </button>
          <div className="sidebar-project-heading">
            我的项目 <span>{projects.length}</span>
          </div>
          <div className="sidebar-project-list" aria-label="我的项目">
            {projects.map((project) => (
              <div className="sidebar-project-row" key={project.project_id}>
                <button
                  className="sidebar-project"
                  title={project.name}
                  aria-current={
                    page !== 'persona' && projectId === project.project_id ? 'page' : undefined
                  }
                  disabled={locked}
                  onClick={() => openProject(project.project_id)}
                >
                  <Icon name="file" size={17} />
                  <span className="sidebar-project-name">{project.name}</span>
                  <span className="nav-indicator" />
                </button>
                <button
                  className="project-delete project-rename"
                  aria-label={`重命名项目：${project.name}`}
                  title="重命名项目"
                  disabled={Boolean(busy) || renameBusy}
                  onClick={() => {
                    setRenamingProject(project)
                    setRenameName(project.name)
                    setRenameError('')
                  }}
                >
                  <Icon name="edit" size={16} />
                </button>
                <button
                  className="project-delete"
                  aria-label={`删除项目：${project.name}`}
                  title="删除项目"
                  disabled={locked || deleteBusy}
                  onClick={(event) => {
                    deleteTrigger.current = event.currentTarget
                    setDeleteError('')
                    setDeletingProject(project)
                  }}
                >
                  <Icon name="trash" size={16} />
                </button>
              </div>
            ))}
            {projects.length === 0 && (
              <p className="sidebar-project-empty">创建项目后会显示在这里</p>
            )}
          </div>
        </nav>
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
              {page === 'persona' ? '数字人像测试' : (selectedProject?.name ?? '项目与素材')}
              {page === 'review' ? ' / 审核报告' : ''}
            </strong>
          </div>
          <span className="mode-badge">
            <span className={`status-dot ${visibleHealth ? 'online' : ''}`} />
            {visibleHealth ? (visibleHealth.mode === 'live' ? '实时模型' : '固定演示') : '等待连接'}
            {visibleHealth && <span className="model-name">{visibleHealth.model}</span>}
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
          {page !== 'persona' && task && (
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
                <button onClick={() => setProgressDismissed(false)}>查看进度</button>
              )}
            </div>
          )}
          {personaVisited && (
            <div hidden={page !== 'persona'}>
              <Jury onMode={setPersonaHealth} />
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
                  navigate('review')
                })
              }
              onDemo={() =>
                void action('打开预设案例', async () => {
                  const r = await post<Review>('/api/demo')
                  await loadReview(r.review_id)
                  await refreshProjects()
                  setTask(null)
                  navigate('review')
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
                  navigate('review')
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
              onAdd={() => navigate('setup')}
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
              onDiscuss={(risk) => review && setRoundtable({ reviewId: review.review_id, risk })}
              onSetup={() => navigate(selectedProject ? 'project' : 'setup')}
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
            AI 辅助审核与数字人像测试，不构成法律意见或投放批准。
          </span>
          <a className="mobile-version-link" href="/?ui=v1">
            查看第一版
          </a>
          <span className="footer-wordmark">Marketing Court</span>
        </footer>
      </div>
      {roundtable && (
        <Suspense fallback={null}>
          <Roundtable target={roundtable} close={() => setRoundtable(null)} />
        </Suspense>
      )}
      {showProgress && !progressDismissed && (
        <div className="review-progress-overlay">
          <section
            className="review-progress-card"
            role="status"
            aria-live="polite"
            aria-label="审核进度"
          >
            <span className="spinner" />
            <h2>{task?.kind === 'rewrite' ? '正在改写与复核' : '正在审核素材'}</h2>
            <p>{pending && task ? taskStage(task.stage) : busy}</p>
            <div
              className="review-progress-track"
              role="progressbar"
              aria-label="审核处理中"
              aria-valuetext={pending && task ? taskStage(task.stage) : busy}
            >
              <span />
            </div>
            <p className="review-progress-help">
              进度按实际处理阶段更新，完成后自动展示结果。已完成步骤会保存，刷新后可恢复。
            </p>
            <button className="secondary" onClick={() => setProgressDismissed(true)}>
              收起进度，后台继续
            </button>
          </section>
        </div>
      )}
      <dialog
        ref={renameDialog}
        className="delete-project-dialog"
        aria-labelledby="rename-title"
        onCancel={(event) => {
          event.preventDefault()
          if (!renameBusy) setRenamingProject(null)
        }}
      >
        <form
          onSubmit={(event) => {
            event.preventDefault()
            void saveProjectName()
          }}
        >
          <h2 id="rename-title">重命名项目</h2>
          <label className="field-label" htmlFor="project-rename-name">
            项目名称
          </label>
          <input
            id="project-rename-name"
            autoFocus
            required
            maxLength={100}
            value={renameName}
            disabled={renameBusy}
            onChange={(event) => setRenameName(event.target.value)}
          />
          {renameError && (
            <p className="delete-dialog-error" role="alert">
              {renameError}
            </p>
          )}
          <div className="delete-dialog-actions">
            <button
              type="button"
              className="secondary"
              disabled={renameBusy}
              onClick={() => setRenamingProject(null)}
            >
              取消
            </button>
            <button className="primary" disabled={renameBusy || !renameName.trim()}>
              {renameBusy ? '正在保存…' : '保存名称'}
            </button>
          </div>
        </form>
      </dialog>
      <dialog
        ref={deleteDialog}
        className="delete-project-dialog"
        aria-labelledby="delete-project-title"
        aria-describedby="delete-project-description"
        onCancel={(event) => {
          event.preventDefault()
          if (!deleteBusy) setDeletingProject(null)
        }}
      >
        <span className="delete-dialog-icon">
          <Icon name="trash" size={24} />
        </span>
        <h2 id="delete-project-title">删除这个项目？</h2>
        <p className="delete-project-name">{deletingProject?.name}</p>
        <p id="delete-project-description">
          该项目的素材、审核记录、改写和讨论记录将一起删除，无法恢复。用户画像库与独立的数字人像测试记录会保留。
        </p>
        {deleteError && (
          <p className="delete-dialog-error" role="alert">
            {deleteError}
          </p>
        )}
        <div className="delete-dialog-actions">
          <button
            className="secondary"
            autoFocus
            disabled={deleteBusy}
            onClick={() => setDeletingProject(null)}
          >
            取消
          </button>
          <button
            className="danger-button"
            disabled={deleteBusy}
            onClick={() => void confirmDelete()}
          >
            {deleteBusy ? '正在删除…' : '确认删除'}
          </button>
        </div>
      </dialog>
    </div>
  )
}
