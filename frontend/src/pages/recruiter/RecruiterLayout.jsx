import { NavLink, Outlet } from 'react-router-dom'

export default function RecruiterLayout() {
  const link = ({ isActive }) => (isActive ? 'nav-link sub active' : 'nav-link sub')
  return (
    <div>
      <nav className="subnav">
        <NavLink to="/recruiter/jobs" className={link}>
          My jobs
        </NavLink>
        <NavLink to="/recruiter/applications" className={link}>
          Applications
        </NavLink>
      </nav>
      <Outlet />
    </div>
  )
}