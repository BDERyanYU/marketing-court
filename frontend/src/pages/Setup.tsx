import { useEffect, useState, type FormEvent } from 'react'
import Icon from '../components/Icon'
import { markets, productCategories } from '../lib/project-options'
import type { DemoCase, Health, Project, ProjectInput } from '../lib/types'

interface Props {
  health: Health | null
  projects: Project[]
  examples: DemoCase[]
  initialProjectId?: string
  busy: boolean
  onDemo: () => void
  onExample: (id: string) => void
  onUpload: (project: ProjectInput, file: File | null, text: string, projectId?: string) => void
}

export default function Setup({
  health,
  projects,
  examples,
  initialProjectId = '',
  busy,
  onDemo,
  onExample,
  onUpload,
}: Props) {
  const [name, setName] = useState('我的环保广告项目')
  const [market, setMarket] = useState<ProjectInput['market']>('GB')
  const [productCategory, setProductCategory] =
    useState<ProjectInput['product_category']>('reusable_bottle')
  const [projectId, setProjectId] = useState(initialProjectId)
  const [inputMode, setInputMode] = useState<'image' | 'text' | 'both'>('image')
  const [copy, setCopy] = useState('')
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
  const canSubmit = Boolean(
    (projectId || name.trim()) &&
    (inputMode === 'image' ? file : inputMode === 'text' ? copy.trim() : file && copy.trim()),
  )
  const selectedMarket = projects.find((p) => p.project_id === projectId)?.market ?? market
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!canSubmit) return
    onUpload(
      { name: name.trim(), market, product_category: productCategory },
      inputMode === 'text' ? null : file,
      inputMode === 'image' ? '' : copy.trim(),
      projectId || undefined,
    )
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>让每一句宣称，都有据可循。</h1>
          <p className="intro">从广告素材到规则依据，再到改写复核。让营销判断多一份证据。</p>
        </div>
      </div>
      <ol className="workflow-strip" aria-label="审核流程">
        <li className="current">
          <span>1</span>
          <div>
            <strong>上传广告素材</strong>
            <small>图片、文案或二者一起</small>
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
            <strong>改写与复核</strong>
            <small>改写文案，再次复核</small>
          </div>
        </li>
      </ol>
      <div className="setup-grid unified-setup">
        <form className="panel upload-panel" onSubmit={submit}>
          <div className="panel-title">
            <div className="title-with-icon">
              <span className="title-icon">
                <Icon name="folder" />
              </span>
              <div>
                <h2>创建一次审核</h2>
                <p>选择项目，添加图片、文案或同时提交</p>
              </div>
            </div>
            <span className="small-tag">{projectId ? '已有项目' : '新项目'}</span>
          </div>
          <div className="setup-inputs">
            <div className="setup-details">
              <label className="field-label" htmlFor="project-choice">
                所属项目
              </label>
              <select
                id="project-choice"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
              >
                <option value="">新建项目</option>
                {projects.map((p) => (
                  <option key={p.project_id} value={p.project_id}>
                    {p.name}
                  </option>
                ))}
              </select>
              {!projectId && (
                <>
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
                        {markets.map((m) => (
                          <option key={m.value} value={m.value}>
                            {m.label}
                            {m.value === 'GB' ? '' : '（规则待接入）'}
                          </option>
                        ))}
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
                        {productCategories.map((c) => (
                          <option key={c.value} value={c.value}>
                            {c.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                </>
              )}
              <p id="supported-review-scope" className="muted small">
                {selectedMarket === 'GB'
                  ? '已接入英国 CMA 通用环保宣称指引。各品类专项规定、视觉暗示与其他风险仍需另行审核。'
                  : '该市场规则待接入：可保存素材、识别文字与提取宣称，暂不作风险判定。'}
              </p>
              <section className="scope-note">
                <Icon name="file" size={21} />
                <div>
                  <h3>同一个项目，保存多次审核</h3>
                  <p>图片与文案可以单独提交，也可以一起检查。每次提交单独保存，保留原始素材。</p>
                </div>
              </section>
            </div>
            <div className="setup-material">
              <fieldset className="input-mode">
                <legend>审核素材</legend>
                <div className="input-mode-options">
                  {(
                    [
                      ['image', '广告图片'],
                      ['text', '广告文案'],
                      ['both', '图片＋文案'],
                    ] as const
                  ).map(([value, label]) => (
                    <label key={value} className={inputMode === value ? 'selected' : ''}>
                      <input
                        type="radio"
                        name="input-mode"
                        value={value}
                        checked={inputMode === value}
                        onChange={() => setInputMode(value)}
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </fieldset>
              {inputMode !== 'text' && (
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
              )}
              {inputMode !== 'image' && (
                <label className="copy-input">
                  广告文案
                  <textarea
                    aria-label="广告文案"
                    value={copy}
                    onChange={(e) => setCopy(e.target.value)}
                    maxLength={8000}
                    rows={inputMode === 'text' ? 9 : 5}
                    placeholder="粘贴需要审核的广告标题、正文或商品描述…"
                    required
                  />
                  <span>
                    {copy.length} / 8000 字符
                    {inputMode === 'both' ? ' · 将与图片识别文字一起检查' : ' · 无需上传图片'}
                  </span>
                </label>
              )}
              {fileError && (
                <p className="inline-error" role="alert">
                  {fileError}
                </p>
              )}
              <p className="privacy-note">
                <Icon name="shield" size={15} />
                素材保存在本机；实时处理会将广告文案与图片识别文字发送给 DeepSeek。
              </p>
              <button
                className="primary wide"
                type="submit"
                disabled={busy || !canSubmit || health?.mode !== 'live'}
              >
                {busy
                  ? '正在处理…'
                  : selectedMarket !== 'GB'
                    ? '保存并提取宣称'
                    : inputMode === 'image'
                      ? '上传并开始审核'
                      : '提交并开始审核'}
                <Icon name="arrow" size={18} />
              </button>
              {health?.mode !== 'live' && (
                <p className="muted small">
                  当前为固定演示模式，可先打开预设案例。启用实时模型后可审核新素材。
                </p>
              )}
            </div>
          </div>
        </form>
      </div>
      <section id="greenlint-cases" className="example-library" aria-label="GreenLint 案例库">
        <div className="section-heading">
          <div>
            <h2>同一套方法，看见风险与边界</h2>
            <p className="intro">三个负面案例，一个正面对照。选择案例，体验审核、改写与复核。</p>
          </div>
          <span className="small-tag">预设案例</span>
        </div>
        <div className="example-grid">
          <article className="example-card negative">
            <div className="example-meta">
              <span className="severity high">负面案例</span>
              <span>英国 / 日用消费品 · 水杯</span>
            </div>
            <h3>水杯「100% 环保」宣称</h3>
            <p>
              一句整体环保承诺，需要多大范围的证据支持？使用预设广告图，体验原图定位与改写复核。
            </p>
            <div className="example-open">
              <span>1 处高风险 · 图片预设</span>
              <button
                className="secondary"
                aria-label="打开预设案例"
                disabled={busy || !health}
                onClick={onDemo}
              >
                查看案例 <Icon name="arrow" size={15} />
              </button>
            </div>
          </article>
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
          水杯图片、坐标与结果为人工预设；另外三例文案来自 GreenLint
          v1.2，未提供原图与商品页链接。示例判定不代表品牌违法或产品获准投放。
        </p>
      </section>
    </>
  )
}
