import { NavLink, Outlet } from 'react-router-dom'

export default function AdminLayout() {
  const link = ({ isActive }) => (isActive ? 'nav-link sub active' : 'nav-link sub')
  return (
    <div>
      <nav className="subnav">
        <NavLink to="/admin" className={link} end>
          Dashboard
        </NavLink>
        <NavLink to="/admin/quizzes" className={link}>
          Quizzes
        </NavLink>
      </nav>
      <Outlet />
    </div>
  )
}