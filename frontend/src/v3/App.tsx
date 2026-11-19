import { useCallback, useEffect, useRef, useState } from 'react'
import Icon, { type IconName } from '../components/Icon'
import { api, post } from '../lib/api'
import { taskError, taskStage } from '../lib/task-status'
import { marketName } from '../lib/project-options'
import type {
  DemoCase,
  Detail,
  Health,
  Meeting,
  Page,
  Persona,
  Review,
  Role,
  Summary,
  Task,
} from './types'
import { Badge, channels, date, states } from './common'
import { MaterialDialog, MeetingDialog, PersonaEditor, PersonaLibrary } from './Forms'
import ProjectPage from './Project'
import MeetingPage from './Meeting'

const STORAGE = 'marketing-court-workspace-v3'
function saved(): {
  page?: Page
  projectId?: string
  reviewId?: string
  meetingId?: string
  taskId?: string
} {
  try {
    return JSON.parse(localStorage.getItem(STORAGE) ?? '{}')
  } catch {
    return {}
  }
}
export default function App() {
  const initial = useRef(saved())
  const [page, setPage] = useState<Page>(initial.current.page ?? 'projects')
  const [health, setHealth] = useState<Health | null>(null)
  const [summaries, setSummaries] = useState<Summary[]>([])
  const [personas, setPersonas] = useState<Persona[]>([])
  const [examples, setExamples] = useState<DemoCase[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [sources, setSources] = useState<
    { source_id: string; title: string; excerpt: string; url: string }[]
  >([])
  const [detail, setDetail] = useState<Detail | null>(null)
  const [reviewId, setReviewId] = useState(initial.current.reviewId ?? '')
  const [meeting, setMeeting] = useState<Meeting | null>(null)
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [task, setTask] = useState<Task | null>(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [ready, setReady] = useState(false)
  const [material, setMaterial] = useState<'new' | 'existing' | null>(null)
  const [meetingIssues, setMeetingIssues] = useState<string[] | null>(null)
  const [personaEditor, setPersonaEditor] = useState<Persona | 'new' | null>(null)
  const [search, setSearch] = useState('')
  const [meetingFilter, setMeetingFilter] = useState('all')
  const actionLock = useRef(false)
  const pending = Boolean(task && ['queued', 'running'].includes(task.status))
  const locked = Boolean(busy) || pending
  const refreshLists = useCallback(async () => {
    const [projects, audience, conferences] = await Promise.all([
      api<Summary[]>('/api/workspace/projects'),
      api<Persona[]>('/api/workspace/personas'),
      api<Meeting[]>('/api/workspace/meetings'),
    ])
    setSummaries(projects)
    setPersonas(audience)
    setMeetings(conferences)
  }, [])
  const loadProject = useCallback(async (id: string) => {
    const result = await api<Detail>(`/api/workspace/projects/${id}`)
    setDetail(result)
    return result
  }, [])
  const action = async (label: string, fn: () => Promise<void>) => {
    if (actionLock.current) return
    actionLock.current = true
    setBusy(label)
    setError('')
    setMessage('')
    try {
      await fn()
    } catch (e) {
      setError(e instanceof Error ? e.message : '操作未完成，请重试。')
    } finally {
      setBusy('')
      actionLock.current = false
    }
  }
  useEffect(() => {
    let stopped = false
    void (async () => {
      try {
        const status = await api<Health>('/health')
        if (stopped) return
        setHealth(status)
        await refreshLists()
        const [catalog, samples] = await Promise.all([
          api<{ roles: Role[]; sources: typeof sources }>('/api/workspace/roles'),
          api<DemoCase[]>('/api/demo-cases'),
        ])
        setRoles(catalog.roles)
        setSources(catalog.sources)
        setExamples(samples)
        if (initial.current.projectId) await loadProject(initial.current.projectId)
        if (initial.current.meetingId)
          setMeeting(await api<Meeting>(`/api/workspace/meetings/${initial.current.meetingId}`))
        if (initial.current.taskId) {
          const restoredTask = await api<Task>(`/api/tasks/${initial.current.taskId}`)
          setTask(restoredTask)
          if (restoredTask.status === 'completed' && restoredTask.result_id) {
            if (restoredTask.kind === 'review') setReviewId(restoredTask.result_id)
            else {
              const rewrite = await api<{ review_id: string }>(
                `/api/rewrites/${restoredTask.result_id}`,
              )
              setReviewId(rewrite.review_id)
            }
          }
        }
      } catch (e) {
        if (!stopped) setError(e instanceof Error ? e.message : '无法恢复工作区。')
      } finally {
        if (!stopped) setReady(true)
      }
    })()
    return () => {
      stopped = true
    }
  }, [refreshLists, loadProject])
  useEffect(() => {
    if (ready)
      localStorage.setItem(
        STORAGE,
        JSON.stringify({
          page,
          projectId: detail?.project.project_id,
          reviewId,
          meetingId: meeting?.meeting_id,
          taskId: task?.task_id,
        }),
      )
  }, [ready, page, detail?.project.project_id, reviewId, meeting?.meeting_id, task?.task_id])
  useEffect(() => {
    if (!pending || !task) return
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const current = await api<Task>(`/api/tasks/${task.task_id}`)
        if (stopped) return
        setTask(current)
        if (current.status === 'completed') {
          const projectId = detail?.project.project_id
          if (projectId) {
            const updated = await loadProject(projectId)
            if (current.kind === 'review') setReviewId(current.result_id ?? '')
            else if (current.result_id) {
              const version = await api<{ review_id: string }>(`/api/rewrites/${current.result_id}`)
              setReviewId(version.review_id)
            }
            setDetail(updated)
            setPage('project')
          }
          await refreshLists()
        } else if (['queued', 'running'].includes(current.status)) timer = setTimeout(poll, 1000)
      } catch (e) {
        if (!stopped) {
          setError(e instanceof Error ? e.message : '读取任务失败')
          timer = setTimeout(poll, 3000)
        }
      }
    }
    timer = setTimeout(poll, 600)
    return () => {
      stopped = true
      clearTimeout(timer)
    }
  }, [pending, task?.task_id, detail?.project.project_id, loadProject, refreshLists])
  useEffect(() => {
    if (!meeting || meeting.status !== 'generating') return
    const timer = setInterval(() => {
      void api<Meeting>(`/api/workspace/meetings/${meeting.meeting_id}`)
        .then(setMeeting)
        .catch(() => {})
    }, 1500)
    return () => clearInterval(timer)
  }, [meeting?.meeting_id, meeting?.status])
  const openProject = (id: string, selected = '') =>
    action('读取项目', async () => {
      const result = await loadProject(id)
      setReviewId(selected || result.reviews[0]?.review_id || '')
      setPage('project')
      setTask(
        result.tasks.find((t) => ['running', 'queued'].includes(t.status)) ??
          (result.tasks[0] && ['failed', 'interrupted'].includes(result.tasks[0].status)
            ? result.tasks[0]
            : null),
      )
    })
  const openMeeting = (id: string) =>
    action('读取会议', async () => {
      const result = await api<Meeting>(`/api/workspace/meetings/${id}`)
      setMeeting(result)
      await loadProject(result.project_id)
      setReviewId(result.review_id)
      setPage('meeting')
    })
  const openExample = (id?: string) =>
    action('打开预设项目', async () => {
      const report = await post<Review>(id ? `/api/demo-cases/${id}` : '/api/demo')
      await loadProject(report.project_id)
      setReviewId(report.review_id)
      setPage('project')
      setTask(null)
      await refreshLists()
    })
  const currentReview = detail?.reviews.find((r) => r.review_id === reviewId) ?? detail?.reviews[0]
  const nav: [Page, IconName, string][] = [
    ['projects', 'folder', '出海营销项目'],
    ['personas', 'spark', '用户画像'],
    ['meetings', 'scales', '圆桌会议'],
    ['library', 'shield', '角色库 / 审核规则'],
    ['settings', 'file', '设置'],
  ]
  const activeNav = page === 'project' ? 'projects' : page === 'meeting' ? 'meetings' : page
  const title = nav.find((n) => n[0] === activeNav)?.[2]
  const createMaterial = async (value: {
    name: string
    market: string
    product_category: string
    channel: string
    language: string
    file: File | null
    text: string
    draft?: boolean
  }) => {
    await action('保存素材', async () => {
      const project =
        material === 'existing' && detail
          ? detail.project
          : await post<{ project_id: string }>('/api/projects', {
              name: value.name,
              market: value.market,
              product_category: value.product_category,
              channel: value.channel,
            })
      const context =
        material === 'existing' && detail
          ? detail.context
          : {
              persona_ids: [],
              language: value.language,
              brand_notes: '',
              market_notes: '',
              archived: false,
            }
      await api(`/api/workspace/projects/${project.project_id}/context`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...context, language: value.language, archived: false }),
      })
      if (value.draft) {
        await loadProject(project.project_id)
        setReviewId('')
        setTask(null)
        setPage('project')
        setMaterial(null)
        await refreshLists()
        return
      }
      const data = new FormData()
      if (value.file) data.append('file', value.file)
      if (value.text) data.append('text', value.text)
      const asset = await api<{ asset_version_id: string }>(
        `/api/projects/${project.project_id}/assets`,
        { method: 'POST', body: data },
      )
      await loadProject(project.project_id)
      setPage('project')
      setMaterial(null)
      setReviewId('')
      setTask(null)
      setTask(await post<Task>(`/api/assets/${asset.asset_version_id}/reviews`))
      await loadProject(project.project_id)
      await refreshLists()
    })
  }
  if (!ready)
    return (
      <div className="initial-loading" role="status">
        正在恢复项目工作台…
      </div>
    )
  return (
    <div className="v3-app">
      <a className="skip-link" href="#main-content">
        跳到主要内容
      </a>
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault()
            setPage('projects')
          }}
        >
          <span className="brand-symbol">
            <Icon name="scales" size={26} />
          </span>
          <span>
            <strong>AI Marketing 审核</strong>
            <small>出海营销合议工作台</small>
          </span>
        </a>
        <p className="sidebar-label">工作空间</p>
        <nav aria-label="主导航">
          {nav.map(([id, icon, label]) => (
            <button
              key={id}
              aria-current={activeNav === id ? 'page' : undefined}
              onClick={() => {
                setPage(id)
                setMessage('')
              }}
            >
              <Icon name={icon} size={19} />
              <span>{label}</span>
              {id === 'meetings' && meetings.filter((m) => m.status !== 'completed').length > 0 && (
                <span className="nav-count">
                  {meetings.filter((m) => m.status !== 'completed').length}
                </span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <Icon name="shield" size={24} />
          <strong>让每个视角，回到同一份证据。</strong>
          <p>素材、画像与审核问题在项目中汇合，讨论结论回到报告。</p>
        </div>
        <div className="version-links">
          <span>
            <i className={health ? 'online' : ''} />
            {health ? '本机服务已连接' : '连接中'}
          </span>
          <div>
            <a href="/?ui=v2">第二版</a>
            <a href="/?ui=v1">第一版</a>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <button className="text-button" onClick={() => setPage('projects')}>
              工作台
            </button>
            <Icon name="chevron" size={12} />
            <strong>{title}</strong>
            {page === 'project' && (
              <>
                <Icon name="chevron" size={12} />
                <span>{detail?.project.name}</span>
              </>
            )}
          </div>
          <Badge tone="version">项目合议版 · v3</Badge>
          <span className="service-status">
            {health?.mode === 'live' ? '实时模型' : '固定演示'}
            <small>{health?.model}</small>
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
          {message && (
            <div className="success-banner" role="status">
              {message}
            </div>
          )}
          {task && (
            <div
              className={`task-banner ${['failed', 'interrupted'].includes(task.status) ? 'failed' : ''}`}
              role="status"
            >
              <div>
                <strong>
                  {task.kind === 'rewrite' ? '改写复核' : '素材审核'} · {taskStage(task.stage)}
                </strong>
                <p>
                  {taskError(task.error) ??
                    (task.status === 'completed'
                      ? '结果已保存到项目。'
                      : '进度自动更新；连接短暂中断时会自动重试，最多尝试 3 次。可刷新页面恢复进度。')}
                </p>
              </div>
              {['failed', 'interrupted'].includes(task.status) ? (
                <button
                  className="secondary"
                  disabled={Boolean(busy)}
                  onClick={() =>
                    void action('重试任务', async () => {
                      setTask(await post<Task>(`/api/tasks/${task.task_id}/retry`))
                      if (detail) await loadProject(detail.project.project_id)
                    })
                  }
                >
                  重试当前任务
                </button>
              ) : (
                !pending && (
                  <button aria-label="关闭任务提示" onClick={() => setTask(null)}>
                    ×
                  </button>
                )
              )}
            </div>
          )}
          {page === 'projects' && (
            <>
              <div className="page-title">
                <div>
                  <div className="eyebrow">出海营销项目</div>
                  <h1>从素材出发，让讨论形成下一步。</h1>
                  <p>在同一个项目里，连接用户画像、审核报告与多角色圆桌。</p>
                </div>
                <button onClick={() => setMaterial('new')} disabled={locked}>
                  ＋ 创建项目
                </button>
              </div>
              <div className="workspace-flow">
                <span>素材与用户画像</span>
                <Icon name="arrow" size={18} />
                <span>审核报告</span>
                <Icon name="arrow" size={18} />
                <span>圆桌会议</span>
                <Icon name="arrow" size={18} />
                <span>结论与复审</span>
              </div>
              <section className="surface project-list">
                <div className="section-title">
                  <h2>
                    我的项目 <Badge>{summaries.length}</Badge>
                  </h2>
                  <input
                    type="search"
                    aria-label="搜索项目"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="搜索项目名称"
                  />
                </div>
                {summaries
                  .filter((s) =>
                    s.project.name.toLocaleLowerCase().includes(search.toLocaleLowerCase()),
                  )
                  .map((s) => (
                    <button
                      key={s.project.project_id}
                      className="record-row"
                      disabled={locked}
                      onClick={() => void openProject(s.project.project_id)}
                    >
                      <div className="project-row-icon">
                        <Icon name="folder" />
                      </div>
                      <div className="row-main">
                        <strong>{s.project.name}</strong>
                        <small>
                          {marketName(s.project.market)} · {channels[s.project.channel]} ·{' '}
                          {date(s.project.created_at)}
                        </small>
                      </div>
                      <span className="record-count">
                        {s.review_count} 次审核 / {s.meeting_count} 场圆桌
                      </span>
                      <Badge tone={s.status}>{states[s.status]}</Badge>
                      <Icon name="chevron" size={17} />
                    </button>
                  ))}
                {!summaries.length && (
                  <div className="empty">
                    <Icon name="folder" size={40} />
                    <h3>给你的出海创意建立一个项目</h3>
                    <p>添加图片或文案，也可以先体验下方的完整示例。</p>
                    <button onClick={() => setMaterial('new')}>创建第一个项目</button>
                  </div>
                )}
              </section>
              <section className="example-library" id="greenlint-cases">
                <div className="section-title">
                  <div>
                    <h2>用四个案例，走一遍完整流程</h2>
                    <p>三个负面案例，一个正面对照。打开后可从审核问题发起圆桌。</p>
                  </div>
                  <Badge>预设演示</Badge>
                </div>
                <div className="example-grid">
                  <Example
                    title="水杯「100% 环保」宣称"
                    description="一句整体环保承诺，需要多大范围的证据支持？"
                    positive={false}
                    market="GB"
                    count={1}
                    busy={locked}
                    open={() => void openExample()}
                  />
                  {examples.map((e) => (
                    <Example
                      key={e.case_id}
                      title={e.title}
                      description={e.description}
                      positive={e.polarity === 'positive'}
                      market={e.market}
                      count={e.expected_risks}
                      busy={locked}
                      open={() => void openExample(e.case_id)}
                    />
                  ))}
                </div>
                <p className="fine-print">
                  水杯图片与报告为人工预设，GreenLint
                  三例为包内文案及预设规则结果。案例不代表违法认定或投放批准。
                </p>
              </section>
            </>
          )}
          {page === 'project' &&
            (detail ? (
              <ProjectPage
                key={`${detail.project.project_id}-${reviewId}-${detail.context.persona_ids.join(',')}-${detail.context.archived}`}
                detail={detail}
                reviewId={reviewId}
                selectReview={setReviewId}
                personas={personas}
                busy={locked}
                saveContext={(context) =>
                  void action('保存项目上下文', async () => {
                    await api(`/api/workspace/projects/${detail.project.project_id}/context`, {
                      method: 'PUT',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify(context),
                    })
                    await loadProject(detail.project.project_id)
                    setMessage('项目上下文已保存，将用于下一轮审核。')
                  })
                }
                saveDecision={(trigger) =>
                  void action('保存审核反馈', async () => {
                    if (!currentReview) return
                    await post(`/api/workspace/reviews/${currentReview.review_id}/decision`, {
                      trigger,
                    })
                    await loadProject(detail.project.project_id)
                  })
                }
                upload={() => setMaterial('existing')}
                derive={() =>
                  void action('派生用户画像', async () => {
                    if (!currentReview) return
                    const persona = await post<Persona>(
                      '/api/workspace/personas/derive/from-review',
                      { project_id: detail.project.project_id, review_id: currentReview.review_id },
                    )
                    await refreshLists()
                    setPersonaEditor(persona)
                    setMessage('已派生待验证的画像。编辑后可在项目右侧选择并保存。')
                  })
                }
                meeting={setMeetingIssues}
                openMeeting={(id) => void openMeeting(id)}
                rewrite={(review, id) =>
                  void action('谨慎改写与复核', async () =>
                    setTask(
                      await post<Task>(`/api/reviews/${review.review_id}/risks/${id}/rewrite`),
                    ),
                  )
                }
                archive={() =>
                  void action('保存项目状态', async () => {
                    await api(`/api/workspace/projects/${detail.project.project_id}/context`, {
                      method: 'PUT',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        ...detail.context,
                        archived: !detail.context.archived,
                      }),
                    })
                    await loadProject(detail.project.project_id)
                    await refreshLists()
                  })
                }
              />
            ) : (
              <div className="surface empty">
                <h2>选择一个出海营销项目</h2>
                <button onClick={() => setPage('projects')}>返回项目列表</button>
              </div>
            ))}
          {page === 'personas' && (
            <PersonaLibrary
              values={personas}
              create={() => setPersonaEditor('new')}
              edit={setPersonaEditor}
            />
          )}
          {page === 'meetings' && (
            <>
              <div className="page-title">
                <div>
                  <h1>圆桌会议</h1>
                  <p>继续进行中的合议，或回看项目里已经形成的结论。</p>
                </div>
              </div>
              <div className="notice">
                新会议从具体项目的审核报告发起。
                <button className="text-button" onClick={() => setPage('projects')}>
                  前往项目
                </button>
              </div>
              <div className="filter-tabs">
                {[
                  ['all', '全部'],
                  ['active', '进行中'],
                  ['completed', '历史会议'],
                ].map(([id, label]) => (
                  <button
                    key={id}
                    className={meetingFilter === id ? 'active' : ''}
                    onClick={() => setMeetingFilter(id)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <section className="surface">
                {meetings
                  .filter(
                    (m) =>
                      meetingFilter === 'all' ||
                      (meetingFilter === 'completed'
                        ? m.status === 'completed'
                        : m.status !== 'completed'),
                  )
                  .map((m) => (
                    <button
                      className="record-row"
                      key={m.meeting_id}
                      disabled={locked}
                      onClick={() => void openMeeting(m.meeting_id)}
                    >
                      <div className="row-main">
                        <strong>{m.title}</strong>
                        <small>
                          {m.project_name} · {date(m.created_at)} · {m.turns.length} 次发言
                        </small>
                      </div>
                      <Badge tone={m.written_back ? 'ok' : ''}>
                        {m.written_back
                          ? '已回写报告'
                          : m.status === 'completed'
                            ? '有结论'
                            : '进行中'}
                      </Badge>
                      <Icon name="chevron" size={18} />
                    </button>
                  ))}
                {!meetings.length && (
                  <div className="empty">
                    <h2>每一场圆桌，都从项目里的问题开始</h2>
                    <p>打开审核报告，选择有争议的问题并邀请角色。</p>
                  </div>
                )}
              </section>
            </>
          )}
          {page === 'meeting' && meeting && (
            <MeetingPage
              key={meeting.meeting_id}
              value={meeting}
              busy={locked}
              advance={async (instruction) => {
                await action('角色正在讨论', async () => {
                  try {
                    setMeeting(
                      await post<Meeting>(`/api/workspace/meetings/${meeting.meeting_id}/advance`, {
                        expected_index: meeting.turns.length,
                        instruction,
                      }),
                    )
                    await refreshLists()
                  } finally {
                    setMeeting(await api<Meeting>(`/api/workspace/meetings/${meeting.meeting_id}`))
                  }
                })
              }}
              writeback={() =>
                void action('回写审核报告', async () => {
                  await post(`/api/workspace/meetings/${meeting.meeting_id}/writeback`)
                  setMeeting(await api<Meeting>(`/api/workspace/meetings/${meeting.meeting_id}`))
                  await loadProject(meeting.project_id)
                  setMessage('圆桌结论已追加到原审核报告，原风险意见保留。')
                  await refreshLists()
                })
              }
              recheck={(text) =>
                void action('提交圆桌修改稿', async () => {
                  setTask(
                    await post<Task>(`/api/workspace/meetings/${meeting.meeting_id}/recheck`, {
                      text,
                    }),
                  )
                  await loadProject(meeting.project_id)
                  setPage('project')
                })
              }
              back={() => void openProject(meeting.project_id, meeting.review_id)}
            />
          )}
          {page === 'library' && (
            <>
              <div className="page-title">
                <div>
                  <h1>角色库 / 审核规则</h1>
                  <p>每个角色有清楚的关注点，每条依据保留来源。</p>
                </div>
              </div>
              <div className="role-library">
                {roles.map((r) => (
                  <article className="surface" key={r.role_id}>
                    <Icon name={r.role_id === 'legal' ? 'shield' : 'spark'} size={24} />
                    <h2>{r.name}</h2>
                    <p>{r.focus}</p>
                    <Badge>可选圆桌角色</Badge>
                  </article>
                ))}
              </div>
              <section className="surface rules-section">
                <h2>当前规则：英国 CMA 环保宣称指引</h2>
                <p>有限监管指引摘录，其他市场、视觉语义、品类与平台专项规定待接入。</p>
                {sources.map((s) => (
                  <div className="source" key={s.source_id}>
                    <a href={s.url} target="_blank" rel="noreferrer">
                      {s.source_id} · {s.title}
                    </a>
                    <q>{s.excerpt}</q>
                  </div>
                ))}
              </section>
            </>
          )}
          {page === 'settings' && (
            <>
              <div className="page-title">
                <div>
                  <h1>设置</h1>
                  <p>本机运行信息与保留版本。</p>
                </div>
              </div>
              <section className="surface settings-panel">
                <h2>运行与数据</h2>
                <dl>
                  <dt>当前版本</dt>
                  <dd>项目合议版 v3</dd>
                  <dt>模式</dt>
                  <dd>{health?.mode === 'live' ? '实时模型' : '固定演示'}</dd>
                  <dt>模型</dt>
                  <dd>{health?.model ?? '未连接'}</dd>
                  <dt>素材与记录</dt>
                  <dd>保存在本机；实时处理将素材文字与所选上下文发送给模型。</dd>
                </dl>
                <h3>保留的界面版本</h3>
                <div className="version-buttons">
                  <a className="secondary button" href="/?ui=v2">
                    打开第二版
                  </a>
                  <a className="secondary button" href="/?ui=v1">
                    打开第一版
                  </a>
                </div>
                <p className="fine-print">
                  各版本的页面状态独立保存，共用既有项目数据。密钥在本机配置中保存，不显示在网页。
                </p>
              </section>
            </>
          )}
        </main>
        <footer className="app-footer">
          <span>AI 辅助审核与模拟合议，不构成法律意见、真实消费者调研或投放批准。</span>
          <span>AI Marketing 审核 · 项目合议版</span>
        </footer>
      </div>
      {material && (
        <MaterialDialog
          detail={material === 'existing' ? detail : null}
          busy={locked}
          close={() => !busy && setMaterial(null)}
          submit={(value) => void createMaterial(value)}
        />
      )}
      {meetingIssues && detail && currentReview && (
        <MeetingDialog
          review={currentReview}
          initial={meetingIssues}
          roles={roles}
          personas={detail.personas}
          busy={locked}
          close={() => !busy && setMeetingIssues(null)}
          submit={(value) =>
            void action('创建圆桌会议', async () => {
              const result = await post<Meeting>(
                `/api/workspace/projects/${detail.project.project_id}/meetings`,
                value,
              )
              setMeeting(result)
              setMeetingIssues(null)
              setPage('meeting')
              await refreshLists()
            })
          }
        />
      )}
      {personaEditor && (
        <PersonaEditor
          original={personaEditor === 'new' ? null : personaEditor}
          busy={locked}
          close={() => !busy && setPersonaEditor(null)}
          save={(value) =>
            void action('保存画像版本', async () => {
              await post(
                personaEditor === 'new'
                  ? '/api/workspace/personas'
                  : `/api/workspace/personas/${personaEditor.persona_id}/versions`,
                value,
              )
              setPersonaEditor(null)
              await refreshLists()
              setMessage('画像已保存，可在项目中选择对应版本。')
            })
          }
        />
      )}
    </div>
  )
}
function Example({
  title,
  description,
  positive,
  market,
  count,
  open,
  busy,
}: {
  title: string
  description: string
  positive: boolean
  market: string
  count: number
  open: () => void
  busy: boolean
}) {
  return (
    <article className={`example-card ${positive ? 'positive' : 'negative'}`}>
      <div className="section-title">
        <Badge tone={positive ? 'ok' : 'risk'}>{positive ? '正面案例' : '负面案例'}</Badge>
        <small>{marketName(market)}</small>
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      <div className="example-open">
        <span>{count ? `${count} 项待核查` : '包内规则未命中风险'}</span>
        <button className="secondary" disabled={busy} onClick={open} aria-label={`打开${title}`}>
          查看案例
        </button>
      </div>
    </article>
  )
}
