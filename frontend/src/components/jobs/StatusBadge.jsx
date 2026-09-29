import { STATUS_LABELS } from '../../lib/labels'

export default function StatusBadge({ status, label }) {
  const text = label || STATUS_LABELS[status] || status
  return <span className={`badge ${status || 'neutral'}`}>{text}</span>
}
