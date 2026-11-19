import { useEffect, useRef, useState, type FormEvent } from 'react'
import Icon from '../components/Icon'
import { api, post, resourceUrl } from '../lib/api'
import {
  metrics,
  votes,
  type Comparison,
  type Member,
  type PersonaPanel,
  type PersonaReport,
  type PersonaSample,
  type Reaction,
} from '../lib/persona-types'
import type { Health } from '../lib/types'

const traitLabels = {
  grounded: '报告支持',
  inferred: '模型推断',
  unknown: '未知',
  user_supplied: '用户填写',
}
const memberName = (member: Member) =>
  member.specification?.persona.name ?? member.name ?? '未命名角色'
const describe = (value: unknown): string =>
  typeof value === 'string' ? value : JSON.stringify(value)

function ReactionCard({ label, value }: { label: string; value: Reaction }) {
  return (
    <article className="persona-reaction">
      <h4>{label}</h4>
      <span className={`persona-vote ${value.vote}`}>{votes[value.vote]}</span>
      <dl>
        {(
          [
            ['理解', value.interpretation],
            ['关注', value.noticed],
            ['可能误读', value.possible_misreading],
            ['信任理由', value.trust_reason],
            ['投票理由', value.vote_reason],
            ['待核实', value.evidence_needed.join('；')],
            ['不确定性', value.uncertainty],
          ] as const
        )
          .filter(([, value]) => value)
          .map(([name, value]) => (
            <div key={name}>
              <dt>{name}</dt>
              <dd>{value}</dd>
            </div>
          ))}
      </dl>
      <div className="persona-scores">
        {Object.entries(metrics).map(([key, label]) => (
          <span key={key}>
            {label}
            <strong>
              {value.scores[key as keyof typeof metrics]}
              <small>/5</small>
            </strong>
          </span>
        ))}
      </div>
    </article>
  )
}

export default function Jury({ onMode }: { onMode: (mode: Health) => void }) {
  const [sample, setSample] = useState<PersonaSample | null>(null)
  const [report, setReport] = useState<PersonaReport | null>(null)
  const [panel, setPanel] = useState<PersonaPanel | null>(null)
  const [comparison, setComparison] = useState<Comparison | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const [selected, setSelected] = useState('report')
  const [manual, setManual] = useState('')
  const [count, setCount] = useState(3)
  const [original, setOriginal] = useState('')
  const [revised, setRevised] = useState('')
  const [busy, setBusy] = useState(true)
  const [restoringFailed, setRestoringFailed] = useState(false)
  const [status, setStatus] = useState('正在读取测试配置…')
  const [error, setError] = useState('')
  const guard = useRef(false)
  const modeCallback = useRef(onMode)
  modeCallback.current = onMode
  const restored = useRef(false)

  const remember = (kind: 'report' | 'panel' | 'comparison', id: string) => {
    const url = `/jury?${new URLSearchParams({ [kind]: id })}`
    sessionStorage.setItem('marketing-persona-record', url)
    if (location.pathname === '/jury') history.replaceState(null, '', url)
  }
  const restorePanel = async (id: string) => {
    const saved = await api<PersonaPanel>(`/api/jury/panels/${id}`)
    const source = await api<PersonaReport>(`/api/jury/reports/${saved.report_id}`)
    setPanel(saved)
    setReport(source)
    setCount(saved.members.length)
    const base = saved.base_persona
    if (base === null) setSelected('report')
    else if (source.personas.some((persona) => persona.persona_id === base.persona_id))
      setSelected(base.persona_id)
    else {
      setSelected('manual')
      setManual(base.traits[0]?.value ?? '')
    }
  }
  const restore = async () => {
    setRestoringFailed(false)
    const config = await api<PersonaSample>('/api/jury/demo')
    setSample(config)
    modeCallback.current({ status: 'ok', mode: config.mode, model: config.model })
    let query = new URLSearchParams(location.search)
    if (!['report', 'panel', 'comparison'].some((key) => query.has(key))) {
      const saved = sessionStorage.getItem('marketing-persona-record')
      if (saved) query = new URL(saved, location.origin).searchParams
    }
    const comparisonId = query.get('comparison'),
      panelId = query.get('panel'),
      reportId = query.get('report')
    if (comparisonId) {
      const saved = await api<Comparison>(
        `/api/jury/comparisons/${encodeURIComponent(comparisonId)}`,
      )
      await restorePanel(saved.panel_id)
      setComparison(saved)
      setOriginal(saved.original_text)
      setRevised(saved.revised_text)
      remember('comparison', saved.comparison_id)
    } else if (panelId) {
      await restorePanel(encodeURIComponent(panelId))
      remember('panel', panelId)
    } else if (reportId) {
      setReport(await api<PersonaReport>(`/api/jury/reports/${encodeURIComponent(reportId)}`))
      remember('report', reportId)
    }
    setStatus('')
  }
  useEffect(() => {
    if (restored.current) return
    restored.current = true
    void restore()
      .catch((e) => {
        setRestoringFailed(true)
        setError(e instanceof Error ? e.message : '读取测试记录失败。')
        setStatus('')
      })
      .finally(() => setBusy(false))
  }, [])
  const action = async (message: string, work: () => Promise<void>) => {
    if (guard.current) return
    guard.current = true
    setBusy(true)
    setError('')
    setStatus(message)
    try {
      await work()
    } catch (e) {
      setError(e instanceof Error ? e.message : '操作失败，请重试。')
      setStatus('')
    } finally {
      guard.current = false
      setBusy(false)
    }
  }
  const upload = async (uploaded: File) => {
    if (uploaded.size > 8 * 1024 * 1024) throw Error('请使用不超过 8 MB 的调研报告。')
    const form = new FormData()
    form.append('file', uploaded)
    const saved = await api<PersonaReport>('/api/jury/reports', { method: 'POST', body: form })
    setReport(saved)
    setPanel(null)
    setComparison(null)
    setSelected('report')
    setManual('')
    remember('report', saved.report_id)
    setStatus('报告已读取。可以直接生成人像，也可以补充目标画像。')
  }
  const submitReport = (event: FormEvent) => {
    event.preventDefault()
    if (file) void action('正在读取报告并提取画像…', () => upload(file))
  }
  const useSample = () =>
    void action('正在读取水杯样例…', async () => {
      const value = sample ?? (await api<PersonaSample>('/api/jury/demo'))
      setOriginal(value.original_text)
      setRevised(value.revised_text)
      await upload(new File([value.report_text], 'bottle-research.txt', { type: 'text/plain' }))
    })
  const derive = (event: FormEvent) => {
    event.preventDefault()
    if (!report) return
    void action('正在根据报告生成人像，请稍候…', async () => {
      const profile =
        selected === 'report'
          ? {}
          : selected === 'manual'
            ? { manual_persona: manual.trim() }
            : { persona_id: selected }
      const saved = await post<PersonaPanel>('/api/jury/panels', {
        report_id: report.report_id,
        member_count: count,
        ...profile,
      })
      setPanel(saved)
      setComparison(null)
      remember('panel', saved.panel_id)
      setStatus('数字人像已保存，可以填写两版文案。')
    })
  }
  const runRemaining = async (saved: Comparison) => {
    let current = saved
    while (current.next_index !== null) {
      setStatus(
        `已保存 ${current.exposures.length}/${current.total_exposures} 次独立反馈，正在评价下一组人像…`,
      )
      try {
        current = await post<Comparison>(
          `/api/jury/comparisons/${current.comparison_id}/advance-members`,
          { expected_index: current.next_index },
        )
        setComparison(current)
      } catch (e) {
        try {
          setComparison(await api<Comparison>(`/api/jury/comparisons/${current.comparison_id}`))
        } catch {
          /* Saved server progress remains available for retry. */
        }
        throw e
      }
    }
    setStatus('全部反馈已保存，可以查看配对结果。')
  }
  const run = (event: FormEvent) => {
    event.preventDefault()
    if (!panel) return
    void action('正在创建 A/B 测试…', async () => {
      const saved = await post<Comparison>('/api/jury/comparisons', {
        panel_id: panel.panel_id,
        original_text: original.trim(),
        revised_text: revised.trim(),
      })
      setComparison(saved)
      remember('comparison', saved.comparison_id)
      await runRemaining(saved)
    })
  }
  const resume = () =>
    comparison &&
    void action('正在恢复测试…', async () => {
      const saved = await api<Comparison>(`/api/jury/comparisons/${comparison.comparison_id}`)
      setComparison(saved)
      await runRemaining(saved)
    })
  const target = report?.personas.find((persona) => persona.persona_id === selected)
  const complete = comparison?.next_index === null
  const step = complete ? 4 : panel ? 3 : report ? 2 : 1
  const reset = () => {
    setReport(null)
    setPanel(null)
    setComparison(null)
    setFile(null)
    if (fileInput.current) fileInput.current.value = ''
    setOriginal('')
    setRevised('')
    setSelected('report')
    setError('')
    setRestoringFailed(false)
    setStatus('')
    sessionStorage.removeItem('marketing-persona-record')
    history.replaceState(null, '', '/jury')
  }
  return (
    <div className="persona-workspace">
      <div className="page-heading">
        <div>
          <h1>数字人像测试</h1>
          <p className="intro">从调研报告中生成人像，听听同一组人对两版文案的不同反应。</p>
        </div>
        {(report || restoringFailed) && (
          <button className="secondary" disabled={busy} onClick={reset}>
            <Icon name="file" size={16} /> 新建测试
          </button>
        )}
      </div>
      <ol className="workflow-strip" aria-label="数字人像测试流程">
        {['上传调研报告', '生成数字人像', 'A/B 测试与结果'].map((label, index) => (
          <li
            key={label}
            className={step === index + 1 ? 'current' : step > index + 1 ? 'done' : ''}
          >
            <span>{step > index + 1 ? <Icon name="check" size={15} /> : index + 1}</span>
            <div>
              <strong>{label}</strong>
              <small>
                {
                  ['提取目标用户与原文依据', '补充画像，设定测试人数', '独立反馈，逐人配对比较'][
                    index
                  ]
                }
              </small>
            </div>
          </li>
        ))}
      </ol>
      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          {restoringFailed ? (
            <button
              className="secondary"
              disabled={busy}
              onClick={() =>
                void action('正在重新读取…', async () => {
                  try {
                    await restore()
                  } catch (e) {
                    setRestoringFailed(true)
                    throw e
                  }
                })
              }
            >
              重新读取
            </button>
          ) : (
            <button aria-label="关闭测试错误" onClick={() => setError('')}>
              ×
            </button>
          )}
        </div>
      )}
      {status && (
        <div className={`persona-status ${busy ? 'working' : ''}`} role="status" aria-live="polite">
          {busy ? <span className="spinner" /> : <Icon name="check" size={17} />}
          <span>{status}</span>
        </div>
      )}
      {sample?.mode === 'demo' && (
        <div className="notice">
          <Icon name="file" size={17} />
          <span>固定演示模式：请使用水杯样例和预设文案。报告、人像和反馈均为演示数据。</span>
        </div>
      )}
      <div className="persona-setup-grid">
        <section className="panel persona-report-panel">
          <div className="panel-title">
            <div className="title-with-icon">
              <span className="title-icon">
                <Icon name="file" />
              </span>
              <div>
                <h2>调研报告</h2>
                <p>让人像的判断有真实上下文</p>
              </div>
            </div>
            {report && <span className="small-tag">已读取</span>}
          </div>
          <form onSubmit={submitReport}>
            <label className={`dropzone persona-dropzone ${file ? 'has-file' : ''}`}>
              <input
                ref={fileInput}
                type="file"
                aria-label="报告文件"
                accept=".txt,.md,.pdf,.docx"
                disabled={busy}
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
              <span className="upload-icon">
                <Icon name="upload" size={24} />
              </span>
              <strong>{file?.name ?? '选择一份调研报告'}</strong>
              <span>TXT、Markdown、PDF 或 DOCX · 最大 8 MB</span>
              <small>PDF 需包含可复制文字</small>
            </label>
            <div className="persona-actions">
              <button className="primary" disabled={busy || !file}>
                上传并提取画像 <Icon name="arrow" size={16} />
              </button>
              <button
                type="button"
                className="secondary"
                disabled={busy || !sample}
                onClick={useSample}
              >
                用水杯样例
              </button>
            </div>
          </form>
          {report && (
            <p className="persona-file">
              <Icon name="check" size={15} /> {report.filename}
            </p>
          )}
          <p className="persona-privacy">
            报告文字与测试文案会发送至已配置的模型；记录保存在本机。
          </p>
        </section>
        <section className="panel persona-target-panel">
          <div className="panel-title">
            <div className="title-with-icon">
              <span className="title-icon">
                <Icon name="spark" />
              </span>
              <div>
                <h2>生成数字人像</h2>
                <p>沿用报告，也可以补充已知客群</p>
              </div>
            </div>
          </div>
          {!report ? (
            <div className="persona-placeholder">
              <Icon name="spark" size={30} />
              <h3>先了解你的目标用户</h3>
              <p>上传报告或使用样例后，选择画像和人数，生成用于测试的数字人像。</p>
            </div>
          ) : (
            <form onSubmit={derive}>
              <label className="field-label" htmlFor="persona-choice">
                补充目标画像（可选）
              </label>
              <select
                id="persona-choice"
                value={selected}
                disabled={busy}
                onChange={(event) => setSelected(event.target.value)}
              >
                <option value="report">仅使用报告正文</option>
                {report.personas.map((persona) => (
                  <option value={persona.persona_id} key={persona.persona_id}>
                    {persona.name}
                  </option>
                ))}
                {report.mode === 'live' && <option value="manual">手动填写画像</option>}
              </select>
              {target && (
                <ul className="persona-traits">
                  {target.traits.map((trait, index) => (
                    <li key={index}>
                      <div>
                        <strong>{trait.attribute}</strong>
                        <span className="small-tag">{traitLabels[trait.status]}</span>
                      </div>
                      <p>{trait.value}</p>
                      {trait.source_quote && <blockquote>原文「{trait.source_quote}」</blockquote>}
                    </li>
                  ))}
                </ul>
              )}
              {selected === 'manual' && (
                <label className="persona-manual">
                  填写画像
                  <textarea
                    maxLength={1000}
                    value={manual}
                    onChange={(event) => setManual(event.target.value)}
                    required
                    disabled={busy}
                    placeholder="描述购买目标、关注因素及使用情境"
                  />
                </label>
              )}
              <div className="persona-count-row">
                <label htmlFor="persona-count">
                  测试人像数
                  <input
                    id="persona-count"
                    type="number"
                    min={1}
                    step={1}
                    value={count}
                    required
                    disabled={busy}
                    onChange={(event) => setCount(Number(event.target.value))}
                  />
                </label>
                <p>
                  每个人像分别阅读 A、B 文案。
                  <br />
                  人数越多，生成和测试时间越长。
                </p>
              </div>
              <button
                className="primary"
                disabled={
                  busy ||
                  !Number.isInteger(count) ||
                  count < 1 ||
                  (selected === 'manual' && !manual.trim())
                }
              >
                <Icon name="spark" size={17} /> 生成人像
              </button>
            </form>
          )}
        </section>
      </div>
      {panel && (
        <section className="panel persona-panel" aria-label="已生成的数字人像">
          <div className="panel-title">
            <div className="title-with-icon">
              <Icon name="spark" />
              <h2>本次测试人像</h2>
              <span className="count-badge">{panel.members.length}</span>
            </div>
            <span className="small-tag">{panel.base_persona?.name ?? '基于调研报告'}</span>
          </div>
          {panel.theories.length > 0 && (
            <p className="intro persona-theories">
              参考依据：
              {panel.theories
                .map((theory) =>
                  theory.title.replace('团队配置的营销理论 Skill', '营销理论与画像分析方法'),
                )
                .join('、')}
            </p>
          )}
          <div className="persona-member-grid">
            {panel.members.map((member, index) => (
              <article className="persona-member" key={member.member_id}>
                <div className="persona-member-heading">
                  <span className="persona-avatar">{index + 1}</span>
                  <div>
                    <h3>{memberName(member)}</h3>
                    <p>数字测试人像</p>
                  </div>
                </div>
                <dl>
                  {Object.entries(member.sampled_values).map(([name, value]) => (
                    <div key={name}>
                      <dt>{name}</dt>
                      <dd>{describe(value)}</dd>
                    </div>
                  ))}
                </dl>
                {member.situation && <p>{member.situation}</p>}
                <details>
                  <summary>
                    {member.specification ? '查看原版人物 JSON' : '查看旧版角色描述'}
                  </summary>
                  <pre>
                    {member.specification
                      ? JSON.stringify(member.specification, null, 2)
                      : [member.persona_prompt, ...(member.assumptions ?? [])].join('\n')}
                  </pre>
                </details>
              </article>
            ))}
          </div>
          {panel.tinytroupe_plan && (
            <details className="persona-plan">
              <summary>查看人像抽样依据</summary>
              <ul>
                {panel.tinytroupe_plan.sample_plan.map((group, index) => (
                  <li key={index}>
                    {Object.entries(group.sampled_values)
                      .map(([name, value]) => `${name}：${describe(value)}`)
                      .join('；')}{' '}
                    · {group.quantity} 人
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}
      <section className="panel persona-compare-panel">
        <div className="panel-title">
          <div className="title-with-icon">
            <span className="title-icon">
              <Icon name="scan" />
            </span>
            <div>
              <h2>A/B 文案测试</h2>
              <p>同一组人像、两次独立阅读，对照理解与信任的变化</p>
            </div>
          </div>
          {!panel && <span className="small-tag">等待生成人像</span>}
        </div>
        <form onSubmit={run}>
          <div className="persona-copy-grid">
            {(
              [
                ['A', '修改前', original, setOriginal],
                ['B', '修改后', revised, setRevised],
              ] as const
            ).map(([variant, label, value, setter]) => (
              <label className="persona-copy" key={variant}>
                <span>
                  <b>{variant}</b>
                  {label}
                  <small>{value.length} / 4000</small>
                </span>
                <textarea
                  aria-label={`${variant} · ${label}`}
                  value={value}
                  maxLength={4000}
                  required
                  disabled={busy}
                  onChange={(event) => setter(event.target.value)}
                  placeholder={variant === 'A' ? '粘贴当前广告文案…' : '粘贴准备测试的修改稿…'}
                />
              </label>
            ))}
          </div>
          <div className="persona-compare-actions">
            <div className="persona-actions">
              <button
                className="primary"
                disabled={busy || !panel || !original.trim() || !revised.trim()}
              >
                运行 A/B 盲测 <Icon name="arrow" size={17} />
              </button>
              {comparison?.next_index != null && (
                <button className="secondary" type="button" disabled={busy} onClick={resume}>
                  继续测试
                </button>
              )}
              {comparison && (
                <a
                  className="secondary"
                  href={resourceUrl(`/api/jury/comparisons/${comparison.comparison_id}`)}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Icon name="download" size={16} /> 结果 JSON
                </a>
              )}
            </div>
            <p className="muted">反馈逐条保存，刷新后可以恢复。</p>
          </div>
        </form>
        {comparison && !complete && (
          <div className="persona-progress">
            <label htmlFor="persona-progress">
              测试进度{' '}
              <span>
                {comparison.exposures.length} / {comparison.total_exposures} 次反馈
              </span>
            </label>
            <progress
              id="persona-progress"
              max={comparison.total_exposures}
              value={comparison.exposures.length}
            />
          </div>
        )}
      </section>
      {comparison && complete && (
        <section className="panel persona-results" id="results">
          <div className="panel-title">
            <div className="title-with-icon">
              <Icon name="check" />
              <h2>测试结果</h2>
              <span className="count-badge">{comparison.pairs.length} 组配对</span>
            </div>
            <span className="small-tag">
              {comparison.mode === 'demo' ? '演示结果' : 'AI 模拟结果'}
            </span>
          </div>
          <p className="intro">{comparison.notice}</p>
          <div className="persona-result-tables">
            <div>
              <h3>进一步了解的意愿</h3>
              <table>
                <thead>
                  <tr>
                    <th>反馈</th>
                    <th>A · 修改前</th>
                    <th>B · 修改后</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(votes).map(([key, label]) => (
                    <tr key={key}>
                      <th scope="row">{label}</th>
                      <td>{comparison.vote_counts?.A[key as keyof typeof votes]}</td>
                      <td>{comparison.vote_counts?.B[key as keyof typeof votes]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div>
              <h3>从 A 到 B 的评分变化</h3>
              <table>
                <thead>
                  <tr>
                    <th>维度</th>
                    <th>升高</th>
                    <th>持平</th>
                    <th>降低</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(metrics).map(([key, label]) => (
                    <tr key={key}>
                      <th scope="row">{label}</th>
                      <td>{comparison.metric_changes?.[key as keyof typeof metrics].higher}</td>
                      <td>{comparison.metric_changes?.[key as keyof typeof metrics].same}</td>
                      <td>{comparison.metric_changes?.[key as keyof typeof metrics].lower}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <h3 className="persona-feedback-heading">逐人查看反馈</h3>
          {comparison.pairs.map((pair) => (
            <details className="persona-pair" key={pair.member_id}>
              <summary>
                {pair.member_name}
                <span>
                  {votes[pair.original.vote]} <Icon name="arrow" size={13} />{' '}
                  {votes[pair.revised.vote]}
                </span>
              </summary>
              <div className="persona-copy-grid">
                <ReactionCard label="A · 修改前" value={pair.original} />
                <ReactionCard label="B · 修改后" value={pair.revised} />
              </div>
            </details>
          ))}
          <details className="persona-plan">
            <summary>核对本次测试文案</summary>
            <div className="persona-copy-grid">
              <div>
                <h4>A · 修改前</h4>
                <p>{comparison.original_text}</p>
              </div>
              <div>
                <h4>B · 修改后</h4>
                <p>{comparison.revised_text}</p>
              </div>
            </div>
          </details>
        </section>
      )}
      <p className="persona-boundary">
        <Icon name="shield" size={16} />{' '}
        数字人像的反馈用于发现待验证的假设，不能替代真人调研或实际投放结果。
      </p>
    </div>
  )
}
