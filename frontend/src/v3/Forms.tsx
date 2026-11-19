import { useState, type FormEvent } from 'react'
import { markets, productCategories, marketName } from '../lib/project-options'
import { Badge, channels, Dialog, goals, PersonaSummary } from './common'
import type { Detail, Persona, Review, Role } from './types'

export function MaterialDialog({
  detail,
  busy,
  close,
  submit,
}: {
  detail: Detail | null
  busy: boolean
  close: () => void
  submit: (value: {
    name: string
    market: string
    product_category: string
    channel: string
    language: string
    file: File | null
    text: string
    draft?: boolean
  }) => void
}) {
  const [name, setName] = useState('我的出海营销项目')
  const [market, setMarket] = useState(detail?.project.market ?? 'GB')
  const [category, setCategory] = useState('reusable_bottle')
  const [channel, setChannel] = useState(detail?.project.channel ?? 'general_advertising')
  const [mode, setMode] = useState('both')
  const [file, setFile] = useState<File | null>(null)
  const [text, setText] = useState('')
  const [language, setLanguage] = useState(detail?.context.language ?? '英语')
  const [error, setError] = useState('')
  const valid =
    (detail || name.trim()) &&
    (mode === 'image' ? file : mode === 'text' ? text.trim() : file && text.trim())
  const send = (e: FormEvent) => {
    e.preventDefault()
    if (valid)
      submit({
        name: name.trim(),
        market,
        product_category: category,
        channel,
        language,
        file: mode === 'text' ? null : file,
        text: mode === 'image' ? '' : text.trim(),
      })
  }
  return (
    <Dialog title={detail ? '添加素材并复审' : '创建出海营销项目'} close={close}>
      <form onSubmit={send}>
        {detail ? (
          <p className="notice">
            {detail.project.name} · {marketName(market)} · 每次提交保存为独立版本
          </p>
        ) : (
          <>
            <label className="field">
              项目名称
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={100}
                required
              />
            </label>
            <div className="form-grid">
              <label className="field">
                目标市场
                <select
                  aria-label="目标市场"
                  value={market}
                  onChange={(e) => setMarket(e.target.value)}
                >
                  {markets.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                      {m.value !== 'GB' ? '（规则待接入）' : ''}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                商品类别
                <select
                  aria-label="商品类别"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  {productCategories.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                投放渠道
                <select
                  aria-label="投放渠道"
                  value={channel}
                  onChange={(e) => setChannel(e.target.value)}
                >
                  {Object.entries(channels).map(([id, label]) => (
                    <option key={id} value={id}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                素材语言
                <input
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  maxLength={80}
                />
              </label>
            </div>
          </>
        )}
        {detail && (
          <label className="field">
            素材语言
            <input value={language} onChange={(e) => setLanguage(e.target.value)} maxLength={80} />
          </label>
        )}
        <fieldset className="choice-group">
          <legend>审核素材</legend>
          {[
            ['image', '广告图片'],
            ['text', '广告文案'],
            ['both', '图片＋文案'],
          ].map(([id, label]) => (
            <label key={id} className={mode === id ? 'selected' : ''}>
              <input
                type="radio"
                name="material-mode"
                checked={mode === id}
                onChange={() => setMode(id)}
              />
              {label}
            </label>
          ))}
        </fieldset>
        {mode !== 'text' && (
          <label className="file-drop">
            <strong>{file ? file.name : '选择广告图片或落地页截图'}</strong>
            <span>PNG / JPG · 最大 10 MB</span>
            <input
              type="file"
              accept="image/png,image/jpeg"
              aria-label="选择广告图片"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (
                  f &&
                  (!['image/png', 'image/jpeg'].includes(f.type) || f.size > 10 * 1024 * 1024)
                ) {
                  setError('请选择不超过 10 MB 的 PNG/JPG 图片。')
                  return
                }
                setFile(f ?? null)
                setError('')
              }}
            />
          </label>
        )}
        {mode !== 'image' && (
          <label className="field">
            广告文案
            <textarea
              aria-label="广告文案"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={6}
              maxLength={8000}
              required
              placeholder="粘贴标题、正文、商品说明或需要一起检查的配文"
            />
            <small>{text.length} / 8000 字符</small>
          </label>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <p className="fine-print">
          {market === 'GB'
            ? '英国规则目前覆盖有限环保文字指引，图片视觉与渠道专项政策未接入。'
            : '该市场仅保存素材、识别文字与提取宣称，暂不作风险判定。'}
          素材保存在本机，实时处理会将文字发送给 DeepSeek。
        </p>
        <footer>
          <button type="button" className="secondary" onClick={close}>
            取消
          </button>
          {!detail && (
            <button
              type="button"
              className="secondary"
              disabled={busy || !name.trim()}
              onClick={() =>
                submit({
                  name: name.trim(),
                  market,
                  product_category: category,
                  channel,
                  language,
                  file: null,
                  text: '',
                  draft: true,
                })
              }
            >
              保存草稿
            </button>
          )}
          <button disabled={busy || !valid}>
            {busy ? '正在提交…' : market === 'GB' ? '保存并开始审核' : '保存并提取宣称'}
          </button>
        </footer>
      </form>
    </Dialog>
  )
}

export function MeetingDialog({
  review,
  initial,
  roles,
  personas,
  busy,
  close,
  submit,
}: {
  review: Review
  initial: string[]
  roles: Role[]
  personas: Persona[]
  busy: boolean
  close: () => void
  submit: (value: unknown) => void
}) {
  const [title, setTitle] = useState('讨论审核争议与修改方向')
  const [selected, setSelected] = useState(initial)
  const [selectedRoles, setRoles] = useState(['consumer', 'brand', 'legal', 'creative'])
  const [goal, setGoal] = useState('direction')
  const [trigger, setTrigger] = useState('disputed')
  const [withPersonas, setWithPersonas] = useState(true)
  const [withMarket, setWithMarket] = useState(true)
  const issues = review.risks.length
    ? review.risks.map((r) => ({ id: r.risk_id, quote: r.claim_quote }))
    : (review.claims ?? []).map((c) => ({ id: c.claim_id, quote: c.claim_text }))
  if (!issues.length)
    issues.push({ id: `report:${review.review_id}`, quote: '复核报告的覆盖范围与证据边界' })
  const toggle = (id: string) =>
    setSelected(selected.includes(id) ? selected.filter((i) => i !== id) : [...selected, id])
  return (
    <Dialog title="发起圆桌会议" close={close}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          submit({
            review_id: review.review_id,
            title: title.trim(),
            issue_ids: selected,
            roles: selectedRoles,
            trigger,
            goal,
            include_personas: withPersonas,
            include_market: withMarket,
          })
        }}
      >
        <label className="field">
          会议议题
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            maxLength={140}
          />
        </label>
        <fieldset className="issue-picker">
          <legend>引用审核问题</legend>
          {issues.map((i) => (
            <label key={i.id}>
              <input
                type="checkbox"
                checked={selected.includes(i.id)}
                onChange={() => toggle(i.id)}
              />
              <span>{i.quote}</span>
            </label>
          ))}
        </fieldset>
        <div className="form-grid">
          <label className="field">
            发起原因
            <select value={trigger} onChange={(e) => setTrigger(e.target.value)}>
              <option value="unsatisfied">对结果不满意</option>
              <option value="high_risk">风险较高</option>
              <option value="disputed">存在争议</option>
            </select>
          </label>
          <label className="field">
            会议目标
            <select value={goal} onChange={(e) => setGoal(e.target.value)}>
              {Object.entries(goals).map(([id, label]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <fieldset className="role-picker">
          <legend>邀请角色（至少 2 位）</legend>
          {roles.map((r) => (
            <label className={selectedRoles.includes(r.role_id) ? 'selected' : ''} key={r.role_id}>
              <input
                type="checkbox"
                checked={selectedRoles.includes(r.role_id)}
                onChange={() =>
                  setRoles(
                    selectedRoles.includes(r.role_id)
                      ? selectedRoles.filter((id) => id !== r.role_id)
                      : [...selectedRoles, r.role_id],
                  )
                }
              />
              <span>
                <strong>{r.name}</strong>
                <small>{r.focus}</small>
              </span>
            </label>
          ))}
        </fieldset>
        <div className="context-choices">
          <label>
            <input
              type="checkbox"
              checked={withPersonas}
              onChange={(e) => setWithPersonas(e.target.checked)}
            />
            带入用户画像（{personas.length} 个版本）
          </label>
          <label>
            <input
              type="checkbox"
              checked={withMarket}
              onChange={(e) => setWithMarket(e.target.checked)}
            />
            带入市场与品牌上下文
          </label>
        </div>
        {withPersonas && personas.length === 0 && (
          <p className="fine-print">
            当前项目未关联画像。可先返回项目选择并保存，再携带画像上下文发起会议。
          </p>
        )}
        <footer>
          <button type="button" className="secondary" onClick={close}>
            取消
          </button>
          <button
            disabled={busy || !title.trim() || selected.length === 0 || selectedRoles.length < 2}
          >
            {busy ? '正在创建…' : '进入圆桌工作区'}
          </button>
        </footer>
      </form>
    </Dialog>
  )
}

export function PersonaEditor({
  original,
  close,
  busy,
  save,
}: {
  original: Persona | null
  close: () => void
  busy: boolean
  save: (value: unknown) => void
}) {
  const [name, setName] = useState(original?.name ?? '')
  const [summary, setSummary] = useState(original?.summary ?? '')
  const [market, setMarket] = useState(original?.market ?? 'GB')
  const [needs, setNeeds] = useState(original?.needs.join('\n') ?? '')
  const [concerns, setConcerns] = useState(original?.concerns.join('\n') ?? '')
  const lines = (value: string) =>
    value
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
  return (
    <Dialog title={original ? '保存画像新版本' : '创建用户画像'} close={close}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save({
            name: name.trim(),
            summary: summary.trim(),
            market,
            needs: lines(needs),
            concerns: lines(concerns),
          })
        }}
      >
        <label className="field">
          画像名称
          <input value={name} onChange={(e) => setName(e.target.value)} maxLength={100} required />
        </label>
        <label className="field">
          目标市场
          <select value={market} onChange={(e) => setMarket(e.target.value)}>
            {markets.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          画像摘要
          <textarea
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            rows={4}
            maxLength={1600}
            required
          />
        </label>
        <div className="form-grid">
          <label className="field">
            需求（每行一条，最多 8 条）
            <textarea rows={4} value={needs} onChange={(e) => setNeeds(e.target.value)} />
          </label>
          <label className="field">
            顾虑（每行一条，最多 8 条）
            <textarea rows={4} value={concerns} onChange={(e) => setConcerns(e.target.value)} />
          </label>
        </div>
        <p className="fine-print">
          用户填写与素材派生的画像均为待验证假设。编辑会保存新版本，原版本继续可查。
        </p>
        <footer>
          <button type="button" className="secondary" onClick={close}>
            取消
          </button>
          <button
            disabled={
              busy ||
              !name.trim() ||
              !summary.trim() ||
              lines(needs).length > 8 ||
              lines(concerns).length > 8
            }
          >
            保存画像{original ? '新版本' : ''}
          </button>
        </footer>
      </form>
    </Dialog>
  )
}

export function PersonaLibrary({
  values,
  create,
  edit,
}: {
  values: Persona[]
  create: () => void
  edit: (value: Persona) => void
}) {
  return (
    <>
      <div className="page-title">
        <div>
          <h1>用户画像</h1>
          <p>保留假设的来源和版本，让每次判断都有受众上下文。</p>
        </div>
        <button onClick={create}>创建画像</button>
      </div>
      <div className="notice">
        从项目报告可派生画像。派生是基于素材的假设，不是消费者调研事实。
        <a href="/jury">打开消费者模拟工具</a>
      </div>
      <div className="persona-grid">
        {values.map((p) => (
          <article className="surface" key={p.persona_id}>
            <div className="section-title">
              <Badge>{marketName(p.market)}</Badge>
              <button className="text-button" onClick={() => edit(p)}>
                编辑并保存新版本
              </button>
            </div>
            <PersonaSummary persona={p} />
            <h3>关注的需求</h3>
            {p.needs.map((n) => (
              <p key={n}>· {n}</p>
            ))}
            <h3>可能的顾虑</h3>
            {p.concerns.map((n) => (
              <p key={n}>· {n}</p>
            ))}
          </article>
        ))}
      </div>
      {!values.length && (
        <div className="surface empty">
          <h2>先认识你希望沟通的人</h2>
          <p>手动创建目标用户画像，或从项目素材中派生，再把它关联到项目。</p>
          <button onClick={create}>创建第一个画像</button>
        </div>
      )}
    </>
  )
}
