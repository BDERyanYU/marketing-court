import { useState, type FormEvent } from 'react'
import type { Health, Project, Review } from '../lib/types'

interface Props {
  health: Health | null
  projects: Project[]
  history: Review[]
  busy: boolean
  onProject: (id: string) => void
  onOpen: (id: string) => void
  onDemo: () => void
  onUpload: (name: string, file: File) => void
}

export default function Setup({
  health,
  projects,
  history,
  busy,
  onProject,
  onOpen,
  onDemo,
  onUpload,
}: Props) {
  const [name, setName] = useState('我的环保广告项目')
  const [file, setFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState('')
  const [dragging, setDragging] = useState(false)
  const choose = (chosen?: File) => {
    if (!chosen) return
    if (!['image/png', 'image/jpeg'].includes(chosen.type) || chosen.size > 10 * 1024 * 1024) {
      setFileError('请使用不超过 10 MB 的 PNG/JPG 图片。')
      return
    }
    setFile(chosen)
    setFileError('')
  }
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (file) onUpload(name.trim(), file)
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">EVIDENCE BEFORE OPINION</p>
          <h1>
            让每一句宣称，
            <br />
            都有据可循<span>。</span>
          </h1>
          <p className="intro">
            从一张广告开始，识别需要证据支持的表达，
            <br className="desktop-only" />
            用可追溯的规则与复核，让讨论更清晰。
          </p>
        </div>
        <div className="chapter-number">
          01
          <span>
            PROJECT
            <br />& ASSET
          </span>
        </div>
      </div>
      <div className="setup-grid">
        <form className="panel upload-panel" onSubmit={submit}>
          <div className="panel-title">
            <h2>创建一次审核</h2>
            <span className="small-tag">文字宣称审核</span>
          </div>
          <label className="field-label" htmlFor="project-name">
            项目名称
          </label>
          <input
            id="project-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={100}
            required
          />
          <div className="field-grid">
            <label>
              目标市场
              <select disabled value="GB">
                <option value="GB">英国 / United Kingdom</option>
              </select>
            </label>
            <label>
              商品类别
              <select disabled value="reusable_bottle">
                <option value="reusable_bottle">日用消费品 · 水杯</option>
              </select>
            </label>
          </div>
          <label
            className={`dropzone ${dragging ? 'dragging' : ''}`}
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragging(false)
              choose(e.dataTransfer.files[0])
            }}
          >
            <input
              type="file"
              accept="image/png,image/jpeg"
              aria-label="选择广告图片"
              onChange={(e) => choose(e.target.files?.[0])}
            />
            <span className="upload-icon">↥</span>
            <strong>{file ? file.name : '将广告图片拖到这里'}</strong>
            <span>
              {file ? `${(file.size / 1024).toFixed(0)} KB · 点击更换` : '或点击选择本地文件'}
            </span>
            <small>PNG / JPG · 最大 10 MB · 不超过 2000 万像素</small>
          </label>
          {fileError && (
            <p className="inline-error" role="alert">
              {fileError}
            </p>
          )}
          <p className="privacy-note">
            文件保存在本机。实时审核会将提取的广告文字发送至 DeepSeek；密钥仅保存在服务端。
          </p>
          <button
            className="primary wide"
            type="submit"
            disabled={busy || !file || !name.trim() || health?.mode !== 'live'}
          >
            {busy ? '正在处理…' : '上传并开始审核'}
            <span>↗</span>
          </button>
          {health?.mode !== 'live' && (
            <p className="muted small">
              当前为固定演示模式，请打开右侧预设案例；实时上传需先配置模型。
            </p>
          )}
        </form>
        <div className="setup-right">
          <section className="demo-card">
            <p className="eyebrow">A CASE TO EXPLORE</p>
            <div className="bottle-illustration" aria-hidden="true">
              <div />
            </div>
            <span className="small-tag">英国 CMA · 环保宣称</span>
            <h2>
              100%
              <br />
              <em>Eco-Friendly.</em>
            </h2>
            <p>
              一个看似简单的承诺，
              <br />
              需要多大范围的证据支持？
            </p>
            <button className="secondary" disabled={busy || !health} onClick={onDemo}>
              打开预设案例 <span>↗</span>
            </button>
            <small>使用人工准备的文字、坐标与审核结果，界面明确标注。</small>
          </section>
          <section className="scope-note">
            <span>本次审核范围</span>
            <p>英国普通消费品环保文字宣称。其他市场、视觉暗示与平台专项政策需要另行审核。</p>
          </section>
        </div>
      </div>
      {projects.length > 0 && (
        <section className="panel history-panel">
          <div className="panel-title">
            <h2>已保存的项目</h2>
            <select
              aria-label="选择历史项目"
              defaultValue=""
              onChange={(e) => onProject(e.target.value)}
            >
              <option value="" disabled>
                选择项目查看版本
              </option>
              {projects.map((p) => (
                <option key={p.project_id} value={p.project_id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div className="history-list">
            {history.map((r) => (
              <button key={r.review_id} onClick={() => onOpen(r.review_id)} disabled={busy}>
                <span>
                  {r.mode === 'demo' ? '预设案例' : '实时审核'} ·{' '}
                  {new Date(r.created_at).toLocaleString('zh-CN')}
                </span>
                <strong>{r.risks.length} 项待核查</strong>
                <span>打开 ↗</span>
              </button>
            ))}
            {history.length === 0 && <p className="muted">选择项目，继续查看已有审核记录。</p>}
          </div>
        </section>
      )}
    </>
  )
}
