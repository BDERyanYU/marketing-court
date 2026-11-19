import Icon from '../components/Icon'
import { marketName } from '../lib/project-options'
import type { Project as ProjectData, Review } from '../lib/types'

export default function Project({
  project,
  history,
  error,
  onRetry,
  busy,
  onOpen,
  onAdd,
}: {
  project: ProjectData
  history: Review[] | null
  error: string
  onRetry: () => void
  busy: boolean
  onOpen: (id: string) => void
  onAdd: () => void
}) {
  return (
    <>
      <div className="page-heading project-heading">
        <div>
          <h1>{project.name}</h1>
          <p className="intro">
            {marketName(project.market)} · 图片与文案的每次审核，都保存在这里。
          </p>
        </div>
        <button className="primary" disabled={busy} onClick={onAdd}>
          <Icon name="upload" size={18} /> 添加素材审核
        </button>
      </div>
      <section className="panel history-panel project-history" aria-label="项目审核记录">
        <div className="panel-title">
          <div className="title-with-icon">
            <Icon name="clock" />
            <h2>审核记录</h2>
            {history && <span className="count-badge">{history.length}</span>}
          </div>
        </div>
        <div className="history-list">
          {error ? (
            <div className="project-empty" role="alert">
              <p>{error}</p>
              <button className="secondary" onClick={onRetry}>
                重新读取
              </button>
            </div>
          ) : history === null ? (
            <p className="muted" role="status">
              正在读取审核记录…
            </p>
          ) : history.length === 0 ? (
            <div className="project-empty">
              <Icon name="file" size={28} />
              <h3>还没有审核记录</h3>
              <p>添加广告图片、文案，或同时提交两者，开始这个项目的首次审核。</p>
              <button className="secondary" disabled={busy} onClick={onAdd}>
                添加素材审核
              </button>
            </div>
          ) : (
            history.map((item) => (
              <button key={item.review_id} onClick={() => onOpen(item.review_id)} disabled={busy}>
                <span>
                  {item.mode === 'demo' ? '预设案例' : '实时审核'} ·{' '}
                  {new Date(item.created_at).toLocaleString('zh-CN')}
                </span>
                <strong>
                  {item.coverage_status === 'unsupported'
                    ? '未作风险判定'
                    : `${item.risks.length} 项待核查`}
                </strong>
                <span>
                  查看报告 <Icon name="arrow" size={15} />
                </span>
              </button>
            ))
          )}
        </div>
      </section>
    </>
  )
}
