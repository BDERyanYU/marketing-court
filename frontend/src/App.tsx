import { useCallback, useEffect, useRef, useState } from 'react'
import { api, post } from './lib/api'
import type { Asset, CourtCase, Health, Page, Project, Review, Rewrite, Task } from './lib/types'
import Setup from './pages/Setup'
import ReviewPage from './pages/Review'
import Court from './pages/Court'

const STORAGE = 'marketing-court-session-v1'
const stages: Record<string,string> = { queued: '等待执行', asset_parsing: '识别图片文字', asset_parsed: '图片解析完成', claims_extracted: '宣称提取完成', retrieval_completed: '规则检索完成', risk_validated: '风险校验完成', rewrite_completed: '改写完成，正在复核', recheck_claims_extracted: '改写宣称提取完成', recheck_retrieval_completed: '改写规则检索完成', recheck_risk_validated: '改写风险校验完成', completed: '处理完成' }

function savedSession(): {page?: Page; reviewId?: string; caseId?: string; taskId?: string} {
  try { return JSON.parse(localStorage.getItem(STORAGE) ?? '{}') } catch { return {} }
}

export default function App() {
  const initial = useRef(savedSession())
  const [page, setPage] = useState<Page>(initial.current.page ?? 'setup')
  const [health, setHealth] = useState<Health|null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [history, setHistory] = useState<Review[]>([])
  const [review, setReview] = useState<Review|null>(null)
  const [asset, setAsset] = useState<Asset|null>(null)
  const [selectedRisk, setSelectedRisk] = useState('')
  const [rewrites, setRewrites] = useState<Rewrite[]>([])
  const [rechecks, setRechecks] = useState<Record<string,Review>>({})
  const [court, setCourt] = useState<CourtCase|null>(null)
  const [task, setTask] = useState<Task|null>(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [auto, setAuto] = useState(false)
  const [restored, setRestored] = useState(false)
  const advancing = useRef(false)
  const refreshProjects = useCallback(async () => setProjects(await api<Project[]>('/api/projects')), [])
  const loadReview = useCallback(async (id: string) => {
    const result = await api<Review>(`/api/reviews/${id}`)
    const [image, versions] = await Promise.all([api<Asset>(`/api/assets/${result.asset_version_id}`), api<Rewrite[]>(`/api/reviews/${id}/rewrites`)])
    const checks = await Promise.all(versions.map(v => api<Review>(`/api/reviews/${v.review_id}`)))
    setReview(result); setAsset(image); setRewrites(versions); setRechecks(Object.fromEntries(checks.map(c => [c.review_id,c])))
    setSelectedRisk(result.risks[0]?.risk_id ?? '')
  }, [])
  const action = async (label: string, fn: () => Promise<void>) => {
    setBusy(label); setError('')
    try { await fn() } catch (e) { setError(e instanceof Error ? e.message : '操作失败，请重试。') }
    finally { setBusy('') }
  }
  useEffect(() => {
    let cancelled = false
    async function restore() {
      try {
        const status = await api<Health>('/health'); if (cancelled) return
        setHealth(status); await refreshProjects()
        if (initial.current.reviewId) await loadReview(initial.current.reviewId)
        if (initial.current.caseId) setCourt(await api<CourtCase>(`/api/cases/${initial.current.caseId}`))
        if (initial.current.taskId) {
          const task = await api<Task>(`/api/tasks/${initial.current.taskId}`)
          setTask(task)
          if (task.kind === 'review' && task.status === 'completed' && task.result_id) await loadReview(task.result_id)
          else if (task.kind === 'review' && !initial.current.reviewId) setAsset(await api<Asset>(`/api/assets/${task.resource_id}`))
        }
      } catch (e) { if (!cancelled) setError(e instanceof Error ? e.message : '恢复失败，请重新打开案例。') }
      finally { if (!cancelled) setRestored(true) }
    }
    void restore(); return () => { cancelled = true }
  }, [refreshProjects,loadReview])
  useEffect(() => {
    if (restored) localStorage.setItem(STORAGE, JSON.stringify({page, reviewId:review?.review_id, caseId:court?.case_id, taskId:task?.task_id}))
  }, [page,review,court,task,restored])
  useEffect(() => {
    if (!task || !['queued','running'].includes(task.status)) return
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try {
        const current = await api<Task>(`/api/tasks/${task!.task_id}`); if (stopped) return
        setTask(current)
        if (current.status === 'completed' && current.result_id) {
          if (current.kind === 'review') await loadReview(current.result_id)
          else if (review) await loadReview(review.review_id)
          setPage('review'); await refreshProjects()
        } else if (['queued','running'].includes(current.status)) timer = setTimeout(poll,1000)
      } catch (e) { if (!stopped) { setError(e instanceof Error ? e.message : '读取进度失败'); timer = setTimeout(poll,3000) } }
    }
    timer = setTimeout(poll,500); return () => { stopped = true; clearTimeout(timer) }
  }, [task?.task_id,task?.status,review?.review_id,loadReview,refreshProjects])
  const advance = useCallback(async () => {
    if (!court?.next_step || advancing.current) return
    advancing.current = true; setBusy('正在生成庭审发言'); setError('')
    try { const result = await post<CourtCase>(`/api/cases/${court.case_id}/advance`, {expected_step:court.next_step}); setCourt(result); if (!result.next_step) setAuto(false) }
    catch (e) { setError(e instanceof Error ? e.message : '庭审推进失败'); setAuto(false) }
    finally { advancing.current = false; setBusy('') }
  }, [court])
  useEffect(() => {
    if (auto && court?.next_step && !busy) { const timer = setTimeout(() => void advance(),600); return () => clearTimeout(timer) }
  }, [auto,court,busy,advance])
  const pending = Boolean(task && ['queued','running'].includes(task.status))
  const locked = Boolean(busy) || pending
  const chooseReview = (id: string) => action('读取审核版本', async () => { await loadReview(id); setTask(null); setCourt(null); setPage('review') })
  return <div className="app-layout">
    <aside className="sidebar"><a className="brand" href="#" onClick={e=>{e.preventDefault();setPage('setup')}}><span className="brand-symbol">M<span>·</span>C</span><span>MARKETING<br/><strong>COURT</strong></span></a><p className="sidebar-label">工作空间 / WORKSPACE</p><nav aria-label="主导航">{([['setup','01','项目与素材'],['review','02','审核工作台'],['court','03','模拟法庭']] as const).map(([key,num,label])=><button key={key} aria-current={page===key?'page':undefined} onClick={()=>setPage(key)}><span>{num}</span>{label}<i>↗</i></button>)}</nav><div className="sidebar-bottom"><span className={`status-dot ${health?'online':''}`}/>{health?'本地服务已连接':'连接本地服务中'}<p>英国 · 环保文字宣称<br/>DEMO RELEASE / 01</p></div></aside>
    <div className="workspace"><header className="topbar"><span>AI Marketing Court <span className="muted">/ {page==='setup'?'项目与素材':page==='review'?'审核工作台':'模拟法庭'}</span></span><span className="mode-badge">{health?.mode==='live'?'实时模型':'固定演示'} · {health?.model??'等待连接'}</span></header><main>
      {error&&<div className="error-banner" role="alert"><span>{error}</span><button aria-label="关闭错误提示" onClick={()=>setError('')}>×</button></div>}
      {task&&<div className={`task-banner ${['failed','interrupted'].includes(task.status)?'failed':''}`} role="status"><div><strong>{task.kind==='review'?'素材审核':'改写复核'} · {stages[task.stage]??task.stage}</strong><p>{task.error??(task.status==='completed'?'结果已保存。':'进度来自后端实际执行状态。')}</p></div>{['failed','interrupted'].includes(task.status)?<button disabled={!!busy} onClick={()=>void action('恢复任务',async()=>setTask(await post<Task>(`/api/tasks/${task.task_id}/retry`)))}>重试此任务 ↗</button>:task.status==='completed'?<button aria-label="关闭完成提示" onClick={()=>setTask(null)}>×</button>:<span className="spinner"/>}</div>}
      {page==='setup'&&<Setup health={health} projects={projects} history={history} busy={locked} onProject={id=>void action('读取历史',async()=>setHistory(await api<Review[]>(`/api/projects/${id}/reviews`)))} onOpen={id=>void chooseReview(id)} onDemo={()=>void action('打开预设案例',async()=>{const r=await post<Review>('/api/demo');await loadReview(r.review_id);await refreshProjects();setTask(null);setCourt(null);setPage('review')})} onUpload={(name,file)=>void action('上传素材',async()=>{const p=await post<Project>('/api/projects',{name});const data=new FormData();data.append('file',file);const a=await api<Asset>(`/api/projects/${p.project_id}/assets`,{method:'POST',body:data});setAsset(a);setReview(null);setCourt(null);setRewrites([]);setPage('review');setTask(await post<Task>(`/api/assets/${a.asset_version_id}/reviews`));await refreshProjects()})}/>}
      {page==='review'&&<ReviewPage review={review} asset={asset} selectedRisk={selectedRisk} rewrites={rewrites} rechecks={rechecks} busy={locked} onSelect={setSelectedRisk} onSetup={()=>setPage('setup')} onVersion={id=>void chooseReview(id)} onRetryStart={()=>asset&&void action('启动审核',async()=>setTask(await post<Task>(`/api/assets/${asset.asset_version_id}/reviews`)))} onRewrite={id=>review&&void action('生成改写',async()=>setTask(await post<Task>(`/api/reviews/${review.review_id}/risks/${id}/rewrite`)))} onAppeal={id=>void action('打开庭审',async()=>{const cases=await api<CourtCase[]>(`/api/risks/${id}/cases`);setCourt(cases[0]??await post<CourtCase>(`/api/risks/${id}/appeals`));setAuto(false);setPage('court')})}/>}
      {page==='court'&&<Court court={court} busy={!!busy} auto={auto} onAuto={()=>setAuto(v=>!v)} onAdvance={()=>void advance()} onBack={()=>setPage('review')}/>}</main><footer>AI 辅助审核与非正式风险复核，不构成法律意见或投放批准。<span>证据可追溯 · 版本可回溯</span></footer></div>
  </div>
}
