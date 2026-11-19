const stages: Record<string, string> = {
  queued: '等待执行',
  asset_parsing: '正在提取素材文字',
  asset_parsed: '文字提取完成',
  context_frozen: '项目上下文已保存',
  extracting_claims: 'DeepSeek 正在提取广告宣称',
  claims_extracted: '宣称提取完成',
  retrieval_completed: '规则检索完成',
  assessing_risks: 'DeepSeek 正在审核风险',
  risk_validated: '风险校验完成',
  checking_audience: 'DeepSeek 正在评估画像匹配',
  audience_checked: '画像匹配评估完成',
  rewrite_completed: '改写完成，正在复核',
  completed: '处理完成',
}

export function taskStage(stage: string): string {
  if (stage.startsWith('recheck_')) return `修改稿复核：${taskStage(stage.slice(8))}`
  return stages[stage] ?? '正在处理'
}

export function taskError(error: string | null): string | null {
  if (error?.includes('Could not contact DeepSeek'))
    return '连接 DeepSeek 时中断。素材和已完成步骤已保存，可重试继续，无需重新上传。'
  if (error?.includes('incomplete or invalid role result'))
    return 'DeepSeek 返回的结果不完整，已保留完成步骤，请重试继续。'
  return error
}
