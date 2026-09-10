import { Shield, Activity, Server, Cpu, Wifi, Radio, Users, Settings, CheckCircle, AlertTriangle } from 'lucide-react';
import { systemHealth } from '../data/mockData';

const statusConfig = {
  operational: { icon: CheckCircle, color: 'text-success', bg: 'bg-green-50', label: 'Operational' },
  degraded: { icon: AlertTriangle, color: 'text-warning', bg: 'bg-amber-50', label: 'Degraded' },
  down: { icon: AlertTriangle, color: 'text-emergency', bg: 'bg-red-50', label: 'Down' },
};

const users = [
  { name: 'Dr. Anand Sharma', role: 'admin', status: 'active', lastLogin: '2 min ago' },
  { name: 'Rajesh Kumar', role: 'officer', status: 'active', lastLogin: '15 min ago' },
  { name: 'Priya Patel', role: 'officer', status: 'active', lastLogin: '1 hr ago' },
  { name: 'Amit Singh', role: 'field', status: 'offline', lastLogin: '3 hr ago' },
  { name: 'Sunita Devi', role: 'public', status: 'active', lastLogin: '30 min ago' },
];

const roleColors = {
  admin: 'bg-purple-100 text-purple-700',
  officer: 'bg-blue-100 text-primary',
  field: 'bg-green-100 text-success',
  public: 'bg-gray-100 text-text-secondary',
};

export default function Admin() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
          <Shield className="w-5 h-5 text-purple-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Admin Panel</h1>
          <p className="text-text-secondary text-sm">System health, model performance, and user management</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { icon: Server, label: 'API Uptime', value: '99.8%', color: 'bg-green-50 text-success' },
          { icon: Cpu, label: 'Model Accuracy', value: '94.2%', color: 'bg-blue-50 text-primary' },
          { icon: Wifi, label: 'PWA Users', value: '3,240', color: 'bg-purple-50 text-purple-600' },
          { icon: Users, label: 'Total Users', value: '12,480', color: 'bg-amber-50 text-warning' },
        ].map((card, i) => (
          <div key={i} className="bg-white rounded-xl border border-border p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-text-secondary">{card.label}</p>
                <p className="text-2xl font-bold mt-1">{card.value}</p>
              </div>
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${card.color}`}>
                <card.icon className="w-5 h-5" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-border p-5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            System Health
          </h2>
          <div className="space-y-3">
            {systemHealth.map((service, i) => {
              const config = statusConfig[service.status];
              return (
                <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-background hover:bg-gray-100 transition-colors">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${config.bg}`}>
                    <config.icon className={`w-4 h-4 ${config.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{service.name}</p>
                    <p className="text-xs text-text-secondary">{service.latency} latency</p>
                  </div>
                  <div className="text-right">
                    <span className={`text-xs font-medium ${config.color}`}>{config.label}</span>
                    <p className="text-xs text-text-secondary">{service.uptime}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-border p-5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Users className="w-4 h-4 text-primary" />
            User Management
          </h2>
          <div className="space-y-3">
            {users.map((user, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-background hover:bg-gray-100 transition-colors">
                <div className="w-9 h-9 bg-primary-light rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-sm font-bold text-primary">{user.name.charAt(0)}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user.name}</p>
                  <p className="text-xs text-text-secondary">Last login: {user.lastLogin}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase ${roleColors[user.role]}`}>
                    {user.role}
                  </span>
                  <div className={`w-2 h-2 rounded-full ${user.status === 'active' ? 'bg-success' : 'bg-gray-300'}`} />
                </div>
              </div>
            ))}
          </div>
          <button className="w-full mt-4 py-2.5 border border-border rounded-xl text-sm font-medium text-text-secondary hover:bg-gray-50 transition-colors flex items-center justify-center gap-2">
            <Settings className="w-4 h-4" />
            Manage All Users
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-border p-5">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-primary" />
          Model Performance
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Prediction Accuracy', value: '94.2%', desc: 'Last 30 days' },
            { label: 'False Positive Rate', value: '3.1%', desc: 'Within tolerance' },
            { label: 'Inference Time', value: '850ms', desc: 'Avg per prediction' },
            { label: 'Training Data', value: '2.4M', desc: 'Data points used' },
          ].map((metric, i) => (
            <div key={i} className="p-4 bg-background rounded-xl">
              <p className="text-xs text-text-secondary">{metric.label}</p>
              <p className="text-xl font-bold mt-1">{metric.value}</p>
              <p className="text-[10px] text-text-secondary mt-1">{metric.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
