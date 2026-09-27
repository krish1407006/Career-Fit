import { NavLink, Outlet } from 'react-router-dom'

const link = ({ isActive }) => (isActive ? 'nav-link sub active' : 'nav-link sub')

export default function AdminLayout() {
  return (
    <div>
      <nav className="subnav">
        <NavLink to="/admin" className={link} end>
          Dashboard
        </NavLink>
        <NavLink to="/admin/accounts" className={link}>
          Accounts
        </NavLink>
        <NavLink to="/admin/quizzes" className={link}>
          Quizzes
        </NavLink>
        <NavLink to="/admin/resumes" className={link}>
          Resumes
        </NavLink>
        <NavLink to="/admin/applications" className={link}>
          Applications
        </NavLink>
        <NavLink to="/admin/attempts" className={link}>
          Quiz attempts
        </NavLink>
        <NavLink to="/admin/interviews" className={link}>
          Interviews
        </NavLink>
        <NavLink to="/admin/super-emails" className={link}>
          Super emails
        </NavLink>
      </nav>
      <Outlet />
    </div>
  )
}
