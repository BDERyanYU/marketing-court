import AssetCanvas from '../components/AssetCanvas'
import Icon from '../components/Icon'
import { resourceUrl } from '../lib/api'
import { marketName, categoryName } from '../lib/project-options'
import type { Asset, Review as ReviewData, Rewrite } from '../lib/types'

interface Props {
  review: ReviewData | null
  asset: Asset | null
  selectedRisk: string
  rewrites: Rewrite[]
  rechecks: Record<string, ReviewData>
  busy: boolean
  onSelect: (id: string) => void
  onDiscuss: (risk: ReviewData['risks'][number]) => void
  onSetup: () => void
  onRetryStart: () => void
  onRewrite: (id: string) => void
  onVersion: (id: string) => void
}
export default function Review({
  review,
  asset,
  selectedRisk,
  rewrites,
  rechecks,
  busy,
  onSelect,
  onDiscuss,
  onSetup,
  onRetryStart,
  onRewrite,
  onVersion,
}: Props) {
  if (!asset)
    return (
      <div className="empty-state">
        <span className="empty-icon">
          <Icon name="scan" size={32} />
        </span>
        <h1>从一份素材开始</h1>
        <p>上传广告或打开预设案例，查看风险与证据。</p>
        <button className="primary" onClick={onSetup}>
          选择素材 <Icon name="arrow" size={17} />
        </button>
      </div>
    )
  return (
    <>
      <div className="page-heading compact">
        <div>
          <h1>每项风险，都能追溯。</h1>
          <p className="intro">
            {review?.example
              ? `${review.example.market === 'GB' ? '英国' : '欧盟'} · ${review.example.category} · ${review.example.title}`
              : review
                ? `${marketName(review.market ?? 'GB')} · ${categoryName(review.product_category ?? 'reusable_bottle')} · 环保宣称`
                : '素材已保存 · 等待检查'}
            {asset.parent_asset_version_id ? ' · 改写文案版本' : ''}
          </p>
        </div>
        {review && (
          <a
            className="secondary"
            href={resourceUrl(`/api/reviews/${review.review_id}/report`)}
            download
          >
            <Icon name="download" size={17} />
            导出 JSON 报告
          </a>
        )}
      </div>
      {review?.mode === 'demo' && (
        <div className="notice">
          <Icon name="file" size={17} />
          <span>
            {review.example
              ? 'GreenLint v1.2 预设文案：规则匹配在本地重现，不调用实时审核；未提供广告原图。'
              : '预设案例：文字、坐标与审核结果由人工准备，不代表实时模型审核。'}
          </span>
        </div>
      )}
      {review?.coverage_status === 'unsupported' && (
        <div className="notice" role="status">
          该市场规则尚未接入。本次仅完成文字识别与宣称提取，未作风险判定。
        </div>
      )}
      {review && (
        <div className="review-summary">
          <span>
            <Icon name="file" size={17} />
            {asset.original_filename}
          </span>
          <span>
            <i className="summary-dot risk-dot" />
            {review.coverage_status === 'unsupported'
              ? '未作风险判定'
              : `${review.risks.length} 项待核查`}
          </span>
          <span>
            <Icon name="shield" size={16} />
            {review.sources.length} 条规则依据
          </span>
          <span className="save-status">
            <Icon name="check" size={16} />
            审核结果已保存
          </span>
        </div>
      )}
      <div className="review-grid">
        <section className="panel asset-panel">
          <div className="panel-title">
            <div className="title-with-icon">
              <Icon name="scan" size={20} />
              <h2>
                {asset.kind === 'text'
                  ? '广告文案'
                  : asset.kind === 'copy'
                    ? '关联原图'
                    : '原始素材'}
              </h2>
            </div>
            <span className="small-tag">
              {asset.kind === 'text'
                ? review?.example
                  ? '文案案例'
                  : '广告文案'
                : `${asset.width} × ${asset.height}`}
            </span>
          </div>
          <AssetCanvas
            asset={asset}
            review={review}
            selectedRisk={selectedRisk}
            onSelect={onSelect}
          />
          {asset.kind !== 'text' &&
            (review?.supplied_text || asset.text) &&
            !asset.parent_asset_version_id && (
              <section className="attached-copy">
                <h3>同时提交的广告文案</h3>
                <AssetCanvas
                  asset={{ ...asset, kind: 'text', text: review?.supplied_text || asset.text }}
                  review={
                    review
                      ? { ...review, original_text: review.supplied_text || asset.text || '' }
                      : null
                  }
                  selectedRisk={selectedRisk}
                  onSelect={onSelect}
                />
              </section>
            )}
          <div className="asset-caption">
            <span>{asset.original_filename}</span>
            <span>{asset.kind === 'text' ? '未提供原始图片' : '点击标注查看风险'}</span>
          </div>
          {asset.kind === 'copy' && (
            <div className="notice">
              此版本只修改文案，图片未改变。当前版本文字：<p>{review?.original_text}</p>
            </div>
          )}
        </section>
        <section className="risk-column">
          <div className="section-heading">
            <h2>审核发现</h2>
            <span>
              {review?.coverage_status === 'unsupported'
                ? '未作风险判定'
                : review
                  ? `${review.risks.length} 项待核查`
                  : '等待审核'}
            </span>
          </div>
          {!review && (
            <div className="panel">
              <p>素材已上传。审核完成后将在此显示结果。</p>
              <button className="secondary" disabled={busy} onClick={onRetryStart}>
                启动 / 查看审核任务 ↗
              </button>
            </div>
          )}
          {review?.risks.map((risk, index) => {
            const rewrite = rewrites.find((w) => w.source_risk_id === risk.risk_id)
            return (
              <article
                key={risk.risk_id}
                id={risk.risk_id}
                className={`risk-card ${selectedRisk === risk.risk_id ? 'active' : ''}`}
              >
                <button
                  className="risk-select"
                  aria-pressed={selectedRisk === risk.risk_id}
                  onClick={() => onSelect(risk.risk_id)}
                >
                  <span className={`severity ${risk.severity}`}>
                    {risk.severity === 'high'
                      ? '高风险'
                      : risk.severity === 'medium'
                        ? '中风险'
                        : '低风险'}
                  </span>
                  <span>
                    风险 {String(index + 1).padStart(2, '0')} ·{' '}
                    {asset.kind === 'text' || risk.input_origin === 'text'
                      ? '文案片段'
                      : risk.location_status === 'located'
                        ? '已定位原文'
                        : '定位待确认'}
                  </span>
                </button>
                <blockquote>{risk.claim_quote}</blockquote>
                <div className="assessment">
                  {risk.assessment === 'requires_substantiation'
                    ? '需要证据支持'
                    : '信息不足，需人工核实'}
                </div>
                {risk.demo_rule_ids?.length ? (
                  <p className="demo-rule-note">
                    包内规则匹配：{risk.demo_rule_ids.join(' / ')}（演示规则编号）
                  </p>
                ) : null}
                <p>{risk.reason}</p>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => onDiscuss(risk)}
                >
                  <Icon name="scales" size={16} /> 圆桌复核
                </button>
                <div className="evidence-gap">
                  <strong>待补材料</strong>
                  {risk.evidence_gaps.map((g) => (
                    <p key={g}>{g}</p>
                  ))}
                </div>
                <details open={selectedRisk === risk.risk_id}>
                  <summary>规则依据 · {risk.source_ids.join(' / ')}</summary>
                  {review.sources
                    .filter((s) => risk.source_ids.includes(s.source_id))
                    .map((s) => (
                      <div className="source" key={s.source_id}>
                        <a href={s.url} target="_blank" rel="noreferrer">
                          {s.source_id} · {s.title} ↗
                        </a>
                        <q>{s.excerpt}</q>
                        <small>
                          监管指引 · 核查 {s.checked_at}
                          {review.example ? '；与包内 LR 规则分开引用' : ''}
                        </small>
                      </div>
                    ))}
                </details>
                {risk.demo_rule_ids?.length ? (
                  <details className="package-rule-note">
                    <summary>包内演示规则说明</summary>
                    <p>
                      以下条款说明随演示包导入，未在本次独立核验。英国案例的法律依据以上方 CMA
                      引用为准；EU 条款不能直接用于英国。
                    </p>
                    {review.example_rules
                      ?.filter((rule) => risk.demo_rule_ids?.includes(rule.rule_id))
                      .map((rule) => (
                        <div className="source" key={rule.rule_id}>
                          <strong>
                            {rule.rule_id} /{' '}
                            {rule.market === 'Both' ? '包内标记 UK / EU' : rule.market}
                          </strong>
                          <p>{rule.citation}</p>
                          <q>{rule.excerpt}</q>
                          <p>{rule.explanation}</p>
                        </div>
                      ))}
                  </details>
                ) : null}
                <div className="risk-actions">
                  <button
                    className="secondary"
                    disabled={busy || !!rewrite}
                    onClick={() => onRewrite(risk.risk_id)}
                  >
                    {rewrite ? '已生成改写' : '谨慎改写与复核'}
                  </button>
                </div>
              </article>
            )
          })}
          {review && review.risks.length === 0 && (
            <div className="panel no-risk">
              <h3>
                {review.coverage_status === 'unsupported'
                  ? '等待接入该市场规则'
                  : review.example?.polarity === 'positive'
                    ? '正面对照：未发现明显风险'
                    : '未识别到本主题待核查项'}
              </h3>
              <p>
                {review.coverage_status === 'unsupported'
                  ? '素材与提取结果已保存。当前没有适用规则，因此不能判断是否存在风险。'
                  : review.example
                    ? `仅表示当前文案在 GreenLint 包内${review.example.market === 'EU' ? '欧盟' : '英国'}演示规则下未命中；产品属性与证明未核验，不代表已获投放批准。`
                    : '检查仅覆盖当前环保文字规则，不表示素材已获得投放批准。'}
              </p>
              {review.example?.polarity === 'positive' && (
                <ul className="positive-reasons">
                  <li>明确写出再生材料及 100% 比例，而非笼统的整体环保承诺。</li>
                  <li>提供 FSC 编号线索，但证书真实性和适用范围仍待核验。</li>
                  <li>“darker than conventional” 比较的是纸张颜色，没有被误判为环保性能比较。</li>
                </ul>
              )}
              {review.coverage_status === 'unsupported' && (
                <>
                  <h4>提取的宣称</h4>
                  {review.claims?.length ? (
                    review.claims.map((c) => (
                      <blockquote key={c.claim_id}>{c.claim_text}</blockquote>
                    ))
                  ) : (
                    <p>未提取到可审核宣称；原始素材已保留。</p>
                  )}
                </>
              )}
            </div>
          )}
        </section>
      </div>
      {rewrites.map((w) => (
        <section className="panel rewrite-panel" key={w.rewrite_id}>
          <div className="panel-title">
            <h2>文案改写与复核</h2>
            <span className="small-tag">已复核 1 次</span>
          </div>
          <div className="copy-comparison">
            <div>
              <p className="copy-label">原始文案</p>
              <p>{w.original_text}</p>
            </div>
            <div>
              <p className="copy-label">建议文案</p>
              <p>{w.revised_text}</p>
            </div>
          </div>
          <p>{w.reason}</p>
          <div className="recheck-result">
            <strong>
              {rechecks[w.review_id]?.risks.length
                ? `复核仍有 ${rechecks[w.review_id].risks.length} 项待核查`
                : '本主题复核未识别到待核查项'}
            </strong>
            <button className="text-button" onClick={() => onVersion(w.review_id)}>
              打开文案版本 ↗
            </button>
          </div>
          <p className="muted small">
            {asset.kind === 'text'
              ? '建议仅删除选中风险句，其余表述未获批准。'
              : '建议仅为文案预览，原图未修改。'}
            其他风险与产品真实性仍需人工确认。
          </p>
        </section>
      ))}
      {review && (
        <section className="limitations">
          <h3>本次检查的边界</h3>
          {review.limitations.map((x) => (
            <p key={x}>· {x}</p>
          ))}
          <small>
            规则版本 {review.rule_pack_version} · 模型 {review.model}
          </small>
        </section>
      )}
    </>
  )
}
