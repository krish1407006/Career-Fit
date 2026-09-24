export default function Stat({ label, value, sub }) {
  return (
    <div className="card stat-card">
      <div className="stat-value">{value === null || value === undefined ? '—' : value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}