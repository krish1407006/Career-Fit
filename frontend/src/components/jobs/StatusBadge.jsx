export const STATUS_LABELS = {
  applied: 'Applied',
  shortlisted: 'Shortlisted',
  interview: 'Interview',
  selected: 'Selected',
  rejected: 'Rejected',
  active: 'Active',
  closed: 'Closed',
}

export default function StatusBadge({ status, label }) {
  const text = label || STATUS_LABELS[status] || status
  return <span className={`badge ${status || 'neutral'}`}>{text}</span>
}