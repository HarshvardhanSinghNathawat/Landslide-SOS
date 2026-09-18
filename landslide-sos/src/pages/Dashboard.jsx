import { useEffect, useState } from 'react';
import { AlertTriangle, Droplets, Mountain, Activity, Radio, TrendingUp, Users, MapPin } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import StatCard from '../components/StatCard';
import AlertBadge from '../components/AlertBadge';
import { api } from '../api/client';
import { formatRelativeTime } from '../utils/formatTime';
import { MAP_TILE_URL, MAP_ATTRIBUTION } from '../utils/tiles';

const createIcon = (color) => L.divIcon({
  className: '',
  html: `<div style="width:14px;height:14px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3)"></div>`,
  iconSize: [14, 14],
  iconAnchor: [7, 7],
});

const riskColors = { red: '#DC2626', yellow: '#EAB308', green: '#16A34A' };

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [rainfall, setRainfall] = useState([]);
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [zones, setZones] = useState([]);
  const [zoneId, setZoneId] = useState('');
  const [hours, setHours] = useState(24);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.dashboardStats(),
      api.alerts({ limit: 6 }),
      api.zones(),
    ])
      .then(([statsData, alertsData, zonesData]) => {
        setStats(statsData);
        setRecentAlerts(alertsData);
        setZones(zonesData);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    api.rainfall(zoneId || undefined, hours)
      .then((data) => setRainfall(data?.points ?? []))
      .catch(() => {});
  }, [zoneId, hours]);

  const zoneLabel =
    zoneId ? (zones.find((z) => String(z.id) === String(zoneId))?.name ?? 'NE Network') : 'NE Network';

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <p className="text-text-secondary text-sm">Loading dashboard…</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-text-secondary text-sm mt-1">Real-time landslide monitoring overview</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard title="Active Alerts" value={stats?.activeAlerts ?? 0} icon={AlertTriangle} color="emergency" />
        <StatCard title="Zones at Risk" value={stats?.zonesMonitored ?? 0} icon={Mountain} color="warning" />
        <StatCard title="SMS Sent Today" value={stats?.smsSentToday ?? 0} icon={Droplets} color="primary" />
        <StatCard title="Lives at Risk" value={stats?.livesAtRisk ?? 0} icon={Users} color="danger" />
        <StatCard title="Rainfall Stations" value={stats?.rainfallStations ?? 0} icon={MapPin} color="success" />
        <StatCard title="Model Accuracy" value={Math.round((stats?.modelAccuracy ?? 0) * 100)} suffix="%" icon={Activity} color="success" />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-border p-5">
          <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
            <h2 className="font-semibold flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              Rainfall Trend ({hours}h)
            </h2>
            <div className="flex items-center gap-2">
              <select
                value={zoneId}
                onChange={(e) => setZoneId(e.target.value)}
                className="text-xs border border-border bg-background rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">All zones · {zoneLabel}</option>
                {zones.map((z) => (
                  <option key={z.id} value={z.id}>{z.name}</option>
                ))}
              </select>
              <div className="flex rounded-lg overflow-hidden border border-border">
                {[24, 48].map((h) => (
                  <button
                    key={h}
                    onClick={() => setHours(h)}
                    className={`px-3 py-1.5 text-xs font-semibold ${
                      hours === h ? 'bg-primary text-white' : 'bg-background text-text-secondary hover:bg-gray-200'
                    }`}
                  >
                    {h}h
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rainfall}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="time" tick={{ fontSize: 12 }} stroke="#94A3B8" />
                <YAxis tick={{ fontSize: 12 }} stroke="#94A3B8" unit="mm" />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0' }}
                />
                <Legend />
                <Line type="monotone" dataKey="value" stroke="#2563EB" strokeWidth={2} dot={false} name="Observed" />
                <Line type="monotone" dataKey="forecast" stroke="#94A3B8" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Forecast" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-border p-5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Radio className="w-4 h-4 text-emergency" />
            Recent Alerts
          </h2>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {recentAlerts.length === 0 ? (
              <p className="text-sm text-text-secondary">No recent alerts</p>
            ) : (
              recentAlerts.slice(0, 6).map(alert => (
                <div key={alert.id} className="flex items-start gap-3 p-3 rounded-lg bg-background hover:bg-gray-100 transition-colors cursor-pointer">
                  <AlertBadge type={alert.type} size="sm" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{alert.zone}</p>
                    <p className="text-xs text-text-secondary">{formatRelativeTime(alert.time)} · {alert.sms} SMS sent</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-border p-5">
        <h2 className="font-semibold mb-4">Risk Zone Map</h2>
        <div className="h-80 rounded-lg overflow-hidden">
          <MapContainer
            center={[26.2, 92.7]}
            zoom={7}
            style={{ height: '100%', width: '100%' }}
            scrollWheelZoom={false}
          >
            <TileLayer
              attribution={MAP_ATTRIBUTION}
              url={MAP_TILE_URL}
            />
            {zones.map(zone => (
              <Marker
                key={zone.id}
                position={[zone.lat, zone.lng]}
                icon={createIcon(riskColors[zone.risk])}
              >
                <Popup>
                  <div className="text-sm">
                    <p className="font-bold">{zone.name}</p>
                    <p>Risk: <span className="uppercase font-semibold">{zone.risk}</span></p>
                    <p>Rainfall: {zone.rainfall}mm</p>
                    <p>SWI: {zone.swi}</p>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      </div>
    </div>
  );
}