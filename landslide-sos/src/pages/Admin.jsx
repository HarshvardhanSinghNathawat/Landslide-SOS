import { useEffect, useState } from 'react';
import { Shield, Activity, Server, Cpu, Radio, Users, CheckCircle, AlertTriangle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

const statusConfig = {
  operational: { icon: CheckCircle, color: 'text-success', bg: 'bg-green-50', label: 'Operational' },
  degraded: { icon: AlertTriangle, color: 'text-warning', bg: 'bg-amber-50', label: 'Degraded' },
  down: { icon: AlertTriangle, color: 'text-emergency', bg: 'bg-red-50', label: 'Down' },
  pending: { icon: AlertTriangle, color: 'text-text-secondary', bg: 'bg-gray-100', label: 'Pending' },
};

const roleColors = {
  admin: 'bg-purple-100 text-purple-700',
  officer: 'bg-blue-100 text-primary',
  public: 'bg-gray-100 text-text-secondary',
};

const COMPONENT_NOTE = {
  'Rainfall API (IMD)': 'Mock ingest active — IMD key off',
  'DEM Processing (SRTM 30m)': 'Offline DEM cache',
  'SWI Engine (3-tank)': 'Derived from rainfall history',
  'Landslide Inventory': 'Events loaded from NE atlas',
  'ML Prediction Model': 'XGBoost risk model',
  'Risk Scheduler (Celery)': '30-min beat configured',
  'SMS Gateway': 'Mock provider (swap to MSG91)',
  'PWA Push Service': 'Planned for Phase 3',
  'GIS Tile Server': 'Planned for Phase 4',
};

export default function Admin() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [health, setHealth] = useState({ status: 'ok', database: 'ok', components: [] });
  const [users, setUsers] = useState([]);
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      return;
    }
    Promise.all([
      api.adminHealth(),
      api.adminUsers(),
      api.adminMetrics(),
    ])
      .then(([h, u, m]) => {
        setHealth(h && h.components ? h : { status: 'ok', database: 'ok', components: [] });
        setUsers(u);
        setMetrics(m);
      })
      .catch(() => {});
  }, [user]);

  if (!user) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-10 text-center">
        <p className="text-text-secondary">Please log in to access admin features.</p>
        <button onClick={() => navigate('/login')} className="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium">Go to Login</button>
      </div>
    );
  }

  if (user.role !== 'admin') {
    return (
      <div className="max-w-7xl mx-auto px-4 py-10 text-center">
        <Shield className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <p className="font-semibold text-lg">Access Denied</p>
        <p className="text-text-secondary text-sm mt-1">Admin privileges required to view this page.</p>
      </div>
    );
  }

  const apiStatus = health?.status === 'ok' ? 'Operational' : health?.status === 'degraded' ? 'Degraded' : '—';

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
          { icon: Server, label: 'API Status', value: apiStatus, color: 'bg-green-50 text-success' },
          { icon: Cpu, label: 'Model Accuracy', value: metrics ? `${(metrics.accuracy * 100).toFixed(1)}%` : '—', color: 'bg-blue-50 text-primary' },
          { icon: Radio, label: 'Model Version', value: metrics?.version || '—', color: 'bg-purple-50 text-purple-600' },
          { icon: Users, label: 'Total Users', value: String(users.length), color: 'bg-amber-50 text-warning' },
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
            {health.components.map((service, i) => {
              const config = statusConfig[service.status] || statusConfig.operational;
              return (
                <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-background hover:bg-gray-100 transition-colors">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${config.bg}`}>
                    <config.icon className={`w-4 h-4 ${config.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{service.name}</p>
                    <p className="text-xs text-text-secondary">{COMPONENT_NOTE[service.name] || service.status}</p>
                  </div>
                  <div className="text-right">
                    <span className={`text-xs font-medium ${config.color}`}>{config.label}</span>
                    {service.uptime && <p className="text-xs text-text-secondary">{service.uptime}</p>}
                    {service.latency && <p className="text-xs text-text-secondary">{service.latency} latency</p>}
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
            {users.map((u) => (
              <div key={u.id} className="flex items-center gap-3 p-3 rounded-xl bg-background hover:bg-gray-100 transition-colors">
                <div className="w-9 h-9 bg-primary-light rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-sm font-bold text-primary">{u.full_name?.charAt(0) || '?'}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{u.full_name}</p>
                  <p className="text-xs text-text-secondary">{u.email}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase ${roleColors[u.role] || 'bg-gray-100 text-text-secondary'}`}>
                    {u.role}
                  </span>
                  <div className={`w-2 h-2 rounded-full ${u.is_active ? 'bg-success' : 'bg-gray-300'}`} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-border p-5">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-primary" />
          Model Performance
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Prediction Accuracy', value: metrics ? `${(metrics.accuracy * 100).toFixed(1)}%` : '—', desc: 'Holdout test set' },
            { label: 'Precision', value: metrics ? `${(metrics.precision * 100).toFixed(1)}%` : '—', desc: 'Positives correctly predicted' },
            { label: 'Recall', value: metrics ? `${(metrics.recall * 100).toFixed(1)}%` : '—', desc: 'True events detected' },
            { label: 'F1 Score', value: metrics ? `${(metrics.f1_score * 100).toFixed(1)}%` : '—', desc: 'Harmonic precision/recall' },
          ].map((metric, i) => (
            <div key={i} className="p-4 bg-background rounded-xl">
              <p className="text-xs text-text-secondary">{metric.label}</p>
              <p className="text-xl font-bold mt-1">{metric.value}</p>
              <p className="text-[10px] text-text-secondary mt-1">{metric.desc}</p>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          {[
            { label: 'ROC-AUC', value: metrics ? `${(metrics.roc_auc * 100).toFixed(1)}%` : '—', desc: 'Discrimination power' },
            { label: 'Training Data', value: metrics ? `${(metrics.n_samples / 1000).toFixed(1)}K` : '—', desc: 'Events + ambient samples' },
            { label: 'Model Features', value: metrics ? String(metrics.n_features) : '—', desc: 'Input variables' },
            { label: 'Model', value: metrics ? metrics.model_name : '—', desc: metrics ? `v${metrics.version}` : 'Not trained' },
          ].map((metric, i) => (
            <div key={`m2-${i}`} className="p-4 bg-background rounded-xl">
              <p className="text-xs text-text-secondary">{metric.label}</p>
              <p className="text-xl font-bold mt-1 truncate">{metric.value}</p>
              <p className="text-[10px] text-text-secondary mt-1">{metric.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}