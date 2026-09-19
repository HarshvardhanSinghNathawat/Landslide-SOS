import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Mountain, Bell, User, LogOut, Menu, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { formatRelativeTime } from '../utils/formatTime';

export default function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    api
      .unreadCount()
      .then((data) => setUnread(data.count || 0))
      .catch(() => {});
    api
      .recentAlerts()
      .then((items) => setNotifications(items))
      .catch(() => {});
  }, [location.pathname]);

  const navLinks = [
    { to: '/dashboard', label: 'Dashboard' },
    { to: '/map', label: 'GIS Map' },
    { to: '/routes', label: 'Safe Routes' },
    { to: '/sos', label: 'SOS' },
    { to: '/alerts', label: 'Alerts' },
  ];

  return (
    <nav className="bg-white border-b border-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2 no-underline">
            <div className="w-9 h-9 bg-primary rounded-lg flex items-center justify-center">
              <Mountain className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-text hidden sm:block">LandslideSOS</span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {navLinks.map(link => (
              <Link
                key={link.to}
                to={link.to}
                className={`px-3 py-2 rounded-lg text-sm font-medium no-underline transition-colors ${
                  location.pathname === link.to
                    ? 'bg-primary-light text-primary'
                    : 'text-text-secondary hover:bg-gray-100'
                }`}
              >
                {link.label}
              </Link>
            ))}
            {user?.role === 'admin' && (
              <Link
                to="/admin"
                className={`px-3 py-2 rounded-lg text-sm font-medium no-underline transition-colors ${
                  location.pathname === '/admin'
                    ? 'bg-primary-light text-primary'
                    : 'text-text-secondary hover:bg-gray-100'
                }`}
              >
                Admin
              </Link>
            )}
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <button
                onClick={() => setNotifOpen(!notifOpen)}
                className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <Bell className="w-5 h-5 text-text-secondary" />
                {unread > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-emergency text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                    {unread}
                  </span>
                )}
              </button>
              {notifOpen && (
                <div className="absolute right-0 top-12 w-80 bg-white rounded-xl shadow-lg border border-border p-3 slide-up">
                  <p className="text-xs font-semibold text-text-secondary uppercase mb-2">Notifications</p>
                  {notifications.length === 0 ? (
                    <p className="text-sm text-text-secondary py-3 text-center">No alerts yet</p>
                  ) : (
                    notifications.slice(0, 3).map(a => (
                      <div key={a.id} className="flex items-start gap-2 p-2 rounded-lg hover:bg-gray-50">
                        <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                          a.type === 'red' ? 'bg-emergency' : 'bg-success'
                        }`} />
                        <div>
                          <p className="text-sm font-medium">{a.zone}</p>
                          <p className="text-xs text-text-secondary">{formatRelativeTime(a.time)}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {user ? (
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-primary-light rounded-full flex items-center justify-center">
                  <User className="w-4 h-4 text-primary" />
                </div>
                <span className="text-sm font-medium hidden sm:block">{user.full_name}</span>
                <button onClick={logout} className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
                  <LogOut className="w-4 h-4 text-text-secondary" />
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="px-4 py-2 bg-primary text-white text-sm font-medium rounded-lg no-underline hover:bg-primary-dark transition-colors"
              >
                Login
              </Link>
            )}

            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="md:hidden p-2 rounded-lg hover:bg-gray-100"
            >
              {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {menuOpen && (
          <div className="md:hidden pb-4 border-t border-border pt-3 slide-up">
            {navLinks.map(link => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMenuOpen(false)}
                className={`block px-3 py-2 rounded-lg text-sm font-medium no-underline ${
                  location.pathname === link.to ? 'bg-primary-light text-primary' : 'text-text-secondary'
                }`}
              >
                {link.label}
              </Link>
            ))}
            {user?.role === 'admin' && (
              <Link
                to="/admin"
                onClick={() => setMenuOpen(false)}
                className="block px-3 py-2 rounded-lg text-sm font-medium text-text-secondary no-underline"
              >
                Admin
              </Link>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}