import { useEffect, useState, useRef, Fragment } from 'react';
import { Search, ChevronDown, ChevronUp, MessageSquare, Users, Clock } from 'lucide-react';
import AlertBadge from '../components/AlertBadge';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import { formatRelativeTime } from '../utils/formatTime';

const statusColors = {
  delivered: 'bg-green-100 text-success',
  acknowledged: 'bg-blue-100 text-primary',
  pending: 'bg-amber-100 text-warning',
};

export default function Alerts() {
  const { user } = useAuth();
  const [expandedId, setExpandedId] = useState(null);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [ackIds, setAckIds] = useState(new Set());
  const debounceRef = useRef(null);

  const canAck = user?.role === 'officer' || user?.role === 'admin';

  const fetchAlerts = (f, s) => {
    setLoading(true);
    api
      .alerts({ level: f === 'all' ? undefined : f, search: s || undefined, limit: 50 })
      .then((items) => {
        setItems(Array.isArray(items) ? items : []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchAlerts(filter, search);
  }, [filter]);

  const handleSearch = (value) => {
    setSearch(value);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchAlerts(filter, value), 350);
  };

  const handleAck = async (id) => {
    try {
      await api.acknowledgeAlert(id);
      setAckIds((prev) => new Set([...prev, id]));
      setItems((prev) => prev.map((a) => (a.id === id ? { ...a, status: 'acknowledged' } : a)));
    } catch {
      /* silently fail for prototype */
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Alert History</h1>
        <p className="text-text-secondary text-sm mt-1">Track all SOS alerts and their delivery status</p>
      </div>

      <div className="bg-white rounded-xl border border-border p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary" />
            <input
              type="text"
              placeholder="Search by zone or alert ID..."
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="flex gap-2">
            {[ 'all', 'red', 'yellow', 'green'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-2 rounded-lg text-xs font-semibold uppercase transition-colors ${
                  filter === f ? 'bg-primary text-white' : 'bg-background text-text-secondary hover:bg-gray-200'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-background">
                <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase">Alert ID</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase">Zone</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase">Level</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase">Status</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase hidden sm:table-cell">Time</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase hidden md:table-cell">SMS Sent</th>
                <th className="w-10"></th>
              </tr>
            </thead>
            <tbody>
              {items.map(alert => (
                <Fragment key={alert.id}>
                  <tr
                    className="border-b border-border hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => setExpandedId(expandedId === alert.id ? null : alert.id)}
                  >
                    <td className="px-4 py-3 text-sm font-mono font-medium">{alert.id}</td>
                    <td className="px-4 py-3 text-sm font-medium">{alert.zone}</td>
                    <td className="px-4 py-3"><AlertBadge type={alert.type} size="sm" /></td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[alert.status] || ''}`}>
                        {alert.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-text-secondary hidden sm:table-cell">{formatRelativeTime(alert.time)}</td>
                    <td className="px-4 py-3 text-sm hidden md:table-cell">{alert.sms.toLocaleString()}</td>
                    <td className="px-4 py-3">
                      {expandedId === alert.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </td>
                  </tr>
                  {expandedId === alert.id && (
                    <tr key={`${alert.id}-detail`}>
                      <td colSpan={7} className="px-4 py-4 bg-blue-50/50">
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                          <div className="flex items-center gap-2">
                            <MessageSquare className="w-4 h-4 text-primary" />
                            <div>
                              <p className="text-xs text-text-secondary">SMS Delivered</p>
                              <p className="font-bold">{alert.sms.toLocaleString()}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Users className="w-4 h-4 text-primary" />
                            <div>
                              <p className="text-xs text-text-secondary">Recipients</p>
                              <p className="font-bold">{alert.recipients.toLocaleString()}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4 text-primary" />
                            <div>
                              <p className="text-xs text-text-secondary">SMS Failed</p>
                              <p className="font-bold">{alert.sms_failed}</p>
                            </div>
                          </div>
                          {canAck && (alert.status === 'pending' && !ackIds.has(alert.id)) && (
                            <div className="flex items-center">
                              <button
                                onClick={(e) => { e.stopPropagation(); handleAck(alert.id); }}
                                className="px-4 py-2 bg-primary text-white text-xs font-semibold rounded-lg hover:bg-primary-dark transition-colors"
                              >
                                Acknowledge
                              </button>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
        {items.length === 0 && !loading && (
          <div className="py-12 text-center text-text-secondary">
            <p className="font-medium">No alerts found</p>
            <p className="text-sm mt-1">Try adjusting your filters or search</p>
          </div>
        )}
        {loading && (
          <div className="py-8 text-center text-text-secondary">
            <p className="text-sm">Loading alerts…</p>
          </div>
        )}
      </div>
    </div>
  );
}