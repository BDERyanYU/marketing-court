import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { InviteePanel, InviteeReference } from './types'

export default function InviteePicker({
  invitee,
  onChange,
  disabled,
}: {
  invitee: InviteeReference | null
  onChange: (value: InviteeReference | null) => void
  disabled: boolean
}) {
  const [panels, setPanels] = useState<InviteePanel[] | null>(null)
  const [unavailable, setUnavailable] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    void api<InviteePanel[]>('/api/discussions/invitees', { signal: controller.signal })
      .then((items) => {
        if (!controller.signal.aborted) setPanels(items)
      })
      .catch(() => {
        if (!controller.signal.aborted) setUnavailable(true)
      })
    return () => controller.abort()
  }, [])

  return (
    <div className="rt-invite">
      <label htmlFor="rt-invitee">邀请数字人像（可选）</label>
      <select
        id="rt-invitee"
        disabled={disabled || !panels?.length}
        value={invitee ? `${invitee.panel_id}:${invitee.member_id}` : ''}
        onChange={(event) => {
          const [panel_id, member_id] = event.target.value.split(':')
          onChange(member_id ? { panel_id, member_id } : null)
        }}
      >
        <option value="">不邀请</option>
        {panels?.map((panel) => (
          <optgroup
            key={panel.panel_id}
            label={[
              panel.report_name || '已保存的测试',
              panel.base_persona_name,
              panel.panel_id.slice(0, 8),
            ].filter(Boolean).join(' · ')}
          >
            {panel.members.map((member) => (
              <option key={member.member_id} value={`${panel.panel_id}:${member.member_id}`}>
                {member.name}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      {unavailable && <p role="status">暂时无法读取已保存的人像。</p>}
      {panels?.length === 0 && <p>在「数字人像测试」生成的人像会出现在这里。</p>}
    </div>
  )
}
