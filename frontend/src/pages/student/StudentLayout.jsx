import { NavLink, Outlet } from 'react-router-dom'

export default function StudentLayout() {
  const link = ({ isActive }) => (isActive ? 'nav-link sub active' : 'nav-link sub')
  return (
    <div>
      <nav className="subnav">
        <NavLink to="/student/profile" className={link}>
          Profile
        </NavLink>
        <NavLink to="/student/jobs" className={link}>
          Jobs
        </NavLink>
        <NavLink to="/student/applications" className={link}>
          My applications
        </NavLink>
        <NavLink to="/student/quizzes" className={link}>
          Quizzes
        </NavLink>
        <NavLink to="/student/interview" className={link}>
          Mock interview
        </NavLink>
      </nav>
      <Outlet />
    </div>
  )
}