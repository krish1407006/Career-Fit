import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/authState'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const navLink = ({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand">
          Career<span>AI</span>
        </Link>
        <nav className="topnav">
          <NavLink to="/" className={navLink} end>
            Dashboard
          </NavLink>
          <NavLink to="/profile" className={navLink}>
            Profile
          </NavLink>
          {user?.is_recruiter && (
            <NavLink to="/recruiter" className={navLink}>
              Recruiter
            </NavLink>
          )}
          {/* Admins get the student area too, so they can exercise the real
              student flow on their own account. */}
          {(user?.role === 'student' || user?.is_admin_role) && (
            <NavLink to="/student" className={navLink}>
              Student
            </NavLink>
          )}
          {user?.is_admin_role && (
            <NavLink to="/admin" className={navLink}>
              Admin
            </NavLink>
          )}
        </nav>
        <div className="topbar-right">
          <span className="topbar-user">
            {user?.username} <em className="role-tag">{user?.role}</em>
          </span>
          <button className="btn btn-ghost" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  )
}