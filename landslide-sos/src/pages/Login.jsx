import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Mountain, Shield, User, Radio } from 'lucide-react';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('public');

  const handleLogin = (e) => {
    e.preventDefault();
    login(role);
    navigate(role === 'admin' ? '/admin' : '/dashboard');
  };

  const handleDemo = (demoRole) => {
    login(demoRole);
    navigate(demoRole === 'admin' ? '/admin' : '/dashboard');
  };

  const roles = [
    { value: 'public', label: 'Public User', icon: User, desc: 'View alerts & maps' },
    { value: 'officer', label: 'Field Officer', icon: Radio, desc: 'Report & manage alerts' },
    { value: 'admin', label: 'Administrator', icon: Shield, desc: 'Full system access' },
  ];

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-primary rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Mountain className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold">Welcome Back</h1>
          <p className="text-text-secondary text-sm mt-1">Sign in to LandslideSOS</p>
        </div>

        <div className="bg-white rounded-2xl border border-border p-6">
          <div className="mb-5">
            <label className="block text-sm font-semibold mb-2">Select Role</label>
            <div className="grid grid-cols-3 gap-2">
              {roles.map(r => (
                <button
                  key={r.value}
                  type="button"
                  onClick={() => setRole(r.value)}
                  className={`p-3 rounded-xl border-2 text-center transition-all ${
                    role === r.value
                      ? 'border-primary bg-primary-light'
                      : 'border-border hover:border-gray-300'
                  }`}
                >
                  <r.icon className={`w-5 h-5 mx-auto ${role === r.value ? 'text-primary' : 'text-text-secondary'}`} />
                  <p className="text-xs font-medium mt-1.5">{r.label}</p>
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.gov.in"
                className="w-full px-4 py-2.5 border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="w-full px-4 py-2.5 border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <button
              type="submit"
              className="w-full py-2.5 bg-primary text-white font-semibold rounded-xl hover:bg-primary-dark transition-colors"
            >
              Sign In
            </button>
          </form>

          <div className="mt-5 pt-5 border-t border-border">
            <p className="text-xs text-text-secondary text-center mb-3">Quick demo access (no auth needed)</p>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleDemo('officer')}
                className="py-2 px-3 bg-background border border-border rounded-xl text-xs font-medium hover:bg-gray-200 transition-colors"
              >
                Demo as Field Officer
              </button>
              <button
                onClick={() => handleDemo('admin')}
                className="py-2 px-3 bg-background border border-border rounded-xl text-xs font-medium hover:bg-gray-200 transition-colors"
              >
                Demo as Admin
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
