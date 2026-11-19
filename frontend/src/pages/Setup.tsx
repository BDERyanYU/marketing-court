import { useEffect, useState, type FormEvent } from 'react'
import Icon from '../components/Icon'
import BottleArt from '../components/BottleArt'
import type { DemoCase, Health, Project, ProjectInput, Review } from '../lib/types'

interface Props {
  health: Health | null
  projects: Project[]
  examples: DemoCase[]
  history: Review[]
  busy: boolean
  onProject: (id: string) => void
  onOpen: (id: string) => void
  onDemo: () => void
  onExample: (id: string) => void
  onUpload: (project: ProjectInput, file: File) => void
}

export default function Setup({
  health,
  projects,
  examples,
  history,
  busy,
  onProject,
  onOpen,
  onDemo,
  onExample,
  onUpload,
}: Props) {
  const [name, setName] = useState('我的环保广告项目')
  const [market, setMarket] = useState<ProjectInput['market']>('GB')
  const [productCategory, setProductCategory] =
    useState<ProjectInput['product_category']>('reusable_bottle')
  const [file, setFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState('')
  const [dragging, setDragging] = useState(false)
  const [preview, setPreview] = useState('')
  useEffect(() => {
    if (!file) {
      setPreview('')
      return
    }
    const url = URL.createObjectURL(file)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])
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
    if (file) onUpload({ name: name.trim(), market, product_category: productCategory }, file)
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>让每一句宣称，都有据可循。</h1>
          <p className="intro">从广告素材到规则依据，再到控辩复核。让营销判断多一份证据。</p>
        </div>
        <span className="page-scope">
          <Icon name="shield" size={17} />
          英国环保宣称审核
        </span>
      </div>
      <ol className="workflow-strip" aria-label="审核流程">
        <li className="current">
          <span>1</span>
          <div>
            <strong>上传广告素材</strong>
            <small>从一张图片开始</small>
          </div>
        </li>
        <li>
          <span>2</span>
          <div>
            <strong>发现风险与依据</strong>
            <small>原图定位，规则可查</small>
          </div>
        </li>
        <li>
          <span>3</span>
          <div>
            <strong>改写或提出异议</strong>
            <small>复核文案，开启庭审</small>
          </div>
        </li>
      </ol>
      <div className="setup-grid">
        <form className="panel upload-panel" onSubmit={submit}>
          <div className="panel-title">
            <div className="title-with-icon">
              <span className="title-icon">
                <Icon name="folder" />
              </span>
              <div>
                <h2>创建一次审核</h2>
                <p>设置项目，并添加你的广告图片</p>
              </div>
            </div>
            <span className="small-tag">新项目</span>
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
              <select
                name="market"
                aria-label="目标市场"
                value={market}
                onChange={(e) => setMarket(e.target.value as ProjectInput['market'])}
                aria-describedby="supported-review-scope"
              >
                <option value="GB">英国 / United Kingdom</option>
              </select>
            </label>
            <label>
              商品类别
              <select
                name="product_category"
                aria-label="商品类别"
                value={productCategory}
                onChange={(e) =>
                  setProductCategory(e.target.value as ProjectInput['product_category'])
                }
                aria-describedby="supported-review-scope"
              >
                <option value="reusable_bottle">日用消费品 · 水杯</option>
              </select>
            </label>
          </div>
          <p id="supported-review-scope" className="muted small">
            当前可选范围：英国市场、日用消费品 · 水杯。环保宣称规则已接入，更多市场与品类待扩展。
          </p>
          <label
            className={`dropzone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
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
            {preview ? (
              <img className="upload-preview" src={preview} alt="已选广告图片预览" />
            ) : (
              <span className="upload-icon">
                <Icon name="upload" size={25} />
              </span>
            )}
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
            <Icon name="shield" size={15} />
            图片保存在本机；实时审核会将识别出的广告文字发送给 DeepSeek。
          </p>
          <button
            className="primary wide"
            type="submit"
            disabled={busy || !file || !name.trim() || health?.mode !== 'live'}
          >
            {busy ? '正在处理…' : '上传并开始审核'}
            <Icon name="arrow" size={18} />
          </button>
          {health?.mode !== 'live' && (
            <p className="muted small">
              当前为固定演示模式，可先打开预设案例。启用实时模型后可审核新素材。
            </p>
          )}
        </form>
        <div className="setup-right">
          <section className="demo-card">
            <div className="demo-card-heading">
              <span className="small-tag">预设案例</span>
              <span>英国 CMA 环保指引</span>
            </div>
            <h2>
              一只水杯，
              <br />
              一句值得追问的承诺。
            </h2>
            <p>
              “100% 环保”的背后，
              <br />
              需要多大范围的证据支持？
            </p>
            <BottleArt />
            <div className="demo-card-bottom">
              <div>
                <strong>体验完整审核流程</strong>
                <span>无需准备素材</span>
              </div>
              <button
                className="demo-open"
                aria-label="打开预设案例"
                disabled={busy || !health}
                onClick={onDemo}
              >
                打开预设案例 <Icon name="arrow" size={18} />
              </button>
            </div>
            <small>案例文字、坐标与审核结果为人工预设。</small>
          </section>
          <section className="scope-note">
            <Icon name="file" size={21} />
            <div>
              <h3>先聚焦文字，让证据说话</h3>
              <p>
                当前覆盖英国普通消费品的环保文字宣称。图片视觉暗示、其他市场与平台政策需另行审核。
              </p>
            </div>
          </section>
        </div>
      </div>
      {examples.length > 0 && (
        <section id="greenlint-cases" className="example-library" aria-label="GreenLint 案例库">
          <div className="section-heading">
            <div>
              <h2>同一套方法，看见风险与边界</h2>
              <p className="intro">GreenLint v1.2 文案案例：两个负面示例，一个正面对照。</p>
            </div>
            <span className="small-tag">预设文案</span>
          </div>
          <div className="example-grid">
            {examples.map((example) => (
              <article className={`example-card ${example.polarity}`} key={example.case_id}>
                <div className="example-meta">
                  <span className={`severity ${example.polarity === 'positive' ? 'low' : 'high'}`}>
                    {example.polarity === 'positive' ? '正面案例' : '负面案例'}
                  </span>
                  <span>
                    {example.market === 'GB' ? '英国' : '欧盟'} / {example.category}
                  </span>
                </div>
                <h3>{example.title}</h3>
                <p>{example.description}</p>
                <div className="example-open">
                  <span>
                    {example.expected_risks
                      ? `${example.expected_risks} 处高风险`
                      : '包内规则未发现明显风险'}
                  </span>
                  <button
                    className="secondary"
                    disabled={busy || !health}
                    onClick={() => onExample(example.case_id)}
                    aria-label={`打开${example.title}`}
                  >
                    查看案例 <Icon name="arrow" size={15} />
                  </button>
                </div>
              </article>
            ))}
          </div>
          <p className="example-disclaimer">
            示例判定不代表品牌违法或产品获准投放。文案来自演示包，未提供原图与商品页链接。
          </p>
        </section>
      )}
      {projects.length > 0 && (
        <section className="panel history-panel">
          <div className="panel-title">
            <div className="title-with-icon">
              <Icon name="clock" />
              <h2>已保存的项目</h2>
              <span className="count-badge">{projects.length}</span>
            </div>
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
