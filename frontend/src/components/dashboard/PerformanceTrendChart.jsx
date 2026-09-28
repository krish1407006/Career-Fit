const W = 640
const H = 200
const PAD = { top: 16, right: 16, bottom: 28, left: 40 }
const GRID = [100, 75, 50, 25, 0]

function y(score) {
  return PAD.top + ((100 - score) / 100) * (H - PAD.top - PAD.bottom)
}

function x(i, n) {
  if (n <= 1) return PAD.left + (W - PAD.left - PAD.right) / 2
  return PAD.left + ((W - PAD.left - PAD.right) * i) / (n - 1)
}

function fmtDate(iso) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export default function PerformanceTrendChart({ points }) {
  const n = points.length
  if (!n) return null

  const line = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${x(i, n)},${y(p.score)}`).join(' ')
  const area = `${line} L${x(n - 1, n)},${H - PAD.bottom} L${x(0, n)},${H - PAD.bottom} Z`

  return (
    <div className="trend-wrap">
      <svg
        className="trend-chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Performance trend of quiz and interview scores"
      >
        {GRID.map((val) => (
          <g key={val}>
            <line
              className="trend-grid"
              x1={PAD.left}
              x2={W - PAD.right}
              y1={y(val)}
              y2={y(val)}
            />
            <text className="trend-axis" x={PAD.left - 8} y={y(val) + 3} textAnchor="end">
              {val}
            </text>
          </g>
        ))}

        <path className="trend-area" d={area} />
        <path className="trend-line" d={line} fill="none" />

        {points.map((p, i) => (
          <g key={`${p.kind}-${i}`} className={`trend-dot ${p.kind}`}>
            <circle cx={x(i, n)} cy={y(p.score)} r="4.5">
              <title>
                {p.label} — {p.kind === 'quiz' ? `${p.raw_score}%` : `${p.raw_score} / ${p.max_score}`}
              </title>
            </circle>
          </g>
        ))}

        {n > 1 && (
          <>
            <text className="trend-date" x={x(0, n)} y={H - 6} textAnchor="middle">
              {fmtDate(points[0].date)}
            </text>
            <text className="trend-date" x={x(n - 1, n)} y={H - 6} textAnchor="middle">
              {fmtDate(points[n - 1].date)}
            </text>
          </>
        )}
      </svg>

      {n > 1 && (
        <div className="trend-legend">
          <span><i className="legend-quiz" /> Quiz score (%)</span>
          <span><i className="legend-interview" /> Interview score (/10 → %)</span>
        </div>
      )}
    </div>
  )
}