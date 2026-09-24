export default function SkillChips({ skills, kind }) {
  if (!skills || !skills.length) return null
  const mod = kind ? ` ${kind}-chip` : ''
  return (
    <div className="chips">
      {skills.map((s) => (
        <span key={s} className={`chip${mod}`}>{s}</span>
      ))}
    </div>
  )
}