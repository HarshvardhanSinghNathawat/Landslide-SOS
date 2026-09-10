import { TrendingUp, TrendingDown } from 'lucide-react';

export default function StatCard({ title, value, change, icon: Icon, color = 'primary', suffix = '' }) {
  const colors = {
    primary: 'bg-primary-light text-primary',
    emergency: 'bg-red-50 text-emergency',
    warning: 'bg-amber-50 text-warning',
    success: 'bg-green-50 text-success',
  };

  return (
    <div className="bg-white rounded-xl border border-border p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-text-secondary font-medium">{title}</p>
          <p className="text-2xl font-bold mt-1 text-text">{value}{suffix}</p>
          {change && (
            <div className={`flex items-center gap-1 mt-2 text-xs font-medium ${change > 0 ? 'text-emergency' : 'text-success'}`}>
              {change > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
              <span>{change > 0 ? '+' : ''}{change}% from yesterday</span>
            </div>
          )}
        </div>
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}
