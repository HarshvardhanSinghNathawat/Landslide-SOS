import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { Route as RouteIcon, MapPin, AlertTriangle, ArrowLeftRight, Shield } from 'lucide-react';
import { api } from '../api/client';
import { MAP_TILE_URL, MAP_ATTRIBUTION } from '../utils/tiles';

const riskColors = { red: '#DC2626', orange: '#F59E0B', yellow: '#EAB308', green: '#16A34A' };

const TOWNS = [
  { id: 'guwahati', name: 'Guwahati (Assam)', lat: 26.1445, lng: 91.7362 },
  { id: 'haflong', name: 'Haflong - Dima Hasao (Assam)', lat: 25.1648, lng: 93.0174 },
  { id: 'silchar', name: 'Silchar (Assam)', lat: 24.8333, lng: 92.7787 },
  { id: 'lumding', name: 'Lumding (Assam)', lat: 25.75, lng: 93.17 },
  { id: 'diphu', name: 'Diphu - Karbi Anglong (Assam)', lat: 25.84, lng: 93.43 },
  { id: 'shillong', name: 'Shillong (Meghalaya)', lat: 25.5788, lng: 91.8933 },
  { id: 'aizawl', name: 'Aizawl (Mizoram)', lat: 23.7271, lng: 92.7176 },
  { id: 'imphal', name: 'Imphal (Manipur)', lat: 24.817, lng: 93.9368 },
  { id: 'agartala', name: 'Agartala (Tripura)', lat: 23.8315, lng: 91.2868 },
];

function FitBounds({ points }) {
  const map = useMap();
  useEffect(() => {
    if (!points || points.length < 2) return;
    const lats = points.map((p) => p[0]);
    const lngs = points.map((p) => p[1]);
    map.fitBounds(
      [
        [Math.min(...lats), Math.min(...lngs)],
        [Math.max(...lats), Math.max(...lngs)],
      ],
      { padding: [40, 40] },
    );
  }, [map, points]);
  return null;
}

function StatusBadge({ status }) {
  const map = {
    direct: { label: 'No danger zones crossed', cls: 'bg-green-50 text-success' },
    unsafe: { label: 'Crosses danger zone(s)', cls: 'bg-red-50 text-emergency' },
    detour: { label: 'Detour recommended', cls: 'bg-amber-50 text-warning' },
  };
  const s = map[status] || map.direct;
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${s.cls}`}>
      {s.label}
    </span>
  );
}

export default function Routes() {
  const [zones, setZones] = useState([]);
  const [origin, setOrigin] = useState({ name: 'Guwahati (Assam)', lat: 26.1445, lng: 91.7362 });
  const [destination, setDestination] = useState({
    name: 'Haflong - Dima Hasao (Assam)',
    lat: 25.1648,
    lng: 93.0174,
  });
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const presets = [
    ...TOWNS,
    ...zones.map((z) => ({ id: `z-${z.id}`, name: z.name, lat: z.lat, lng: z.lng })),
  ];

  const buildPoints = (p) => {
    const pts = [];
    if (!p) return pts;
    pts.push(p.start, p.end);
    p.direct.path.forEach((pt) => pts.push(pt));
    p.recommended.path.forEach((pt) => pts.push(pt));
    p.avoided_zones.forEach((z) => pts.push([z.lat, z.lng]));
    p.caution_zones.forEach((z) => pts.push([z.lat, z.lng]));
    return pts;
  };

  useEffect(() => {
    api
      .zones()
      .then(setZones)
      .catch(() => {});
  }, []);

  const runPlan = async (o, d) => {
    if (!o || !d) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.planRoute({
        start_lat: o.lat,
        start_lng: o.lng,
        end_lat: d.lat,
        end_lng: d.lng,
      });
      setPlan(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const applyPreset = (which, id) => {
    const preset = presets.find((p) => p.id === id);
    if (!preset) return;
    if (which === 'origin') setOrigin({ name: preset.name, lat: preset.lat, lng: preset.lng });
    else setDestination({ name: preset.name, lat: preset.lat, lng: preset.lng });
  };

  const swap = () => {
    setOrigin(destination);
    setDestination(origin);
  };

  const deltaKm = plan && plan.recommended.km - plan.direct.km;
  const detourActive = plan && plan.recommended.status === 'detour';

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <div className="bg-white border-b border-border px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-green-100 rounded-xl flex items-center justify-center">
            <RouteIcon className="w-5 h-5 text-success" />
          </div>
          <div>
            <h1 className="font-semibold text-lg">Safe Route Planner</h1>
            <p className="text-xs text-text-secondary">Find routes that avoid landslide-danger areas in Northeast India</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-text-secondary">
          <Shield className="w-4 h-4 text-success" />
          Danger zones (red/orange) are detoured · yellow zones warn
        </div>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row min-h-0">
        <aside className="w-full lg:w-80 lg:shrink-0 border-b lg:border-b-0 lg:border-r border-border bg-white overflow-y-auto p-4 space-y-4">
          <div className="space-y-3">
            <div>
              <label className="text-xs font-semibold text-text-secondary uppercase">Origin</label>
              <select
                value={presets.find((p) => p.lat === origin.lat && p.lng === origin.lng)?.id || ''}
                onChange={(e) => applyPreset('origin', e.target.value)}
                className="mt-1 w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">— choose or type coords —</option>
                {presets.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-2 mt-2">
                <input
                  type="number"
                  step="0.0001"
                  value={origin.lat}
                  onChange={(e) => setOrigin({ ...origin, lat: parseFloat(e.target.value) || 0 })}
                  placeholder="Latitude"
                  className="px-3 py-1.5 border border-border rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <input
                  type="number"
                  step="0.0001"
                  value={origin.lng}
                  onChange={(e) => setOrigin({ ...origin, lng: parseFloat(e.target.value) || 0 })}
                  placeholder="Longitude"
                  className="px-3 py-1.5 border border-border rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <button onClick={swap} className="w-full flex items-center justify-center gap-2 py-1.5 rounded-lg bg-gray-100 text-text-secondary text-xs font-medium hover:bg-gray-200 transition-colors">
              <ArrowLeftRight className="w-3.5 h-3.5" />
              Swap Origin &amp; Destination
            </button>

            <div>
              <label className="text-xs font-semibold text-text-secondary uppercase">Destination</label>
              <select
                value={presets.find((p) => p.lat === destination.lat && p.lng === destination.lng)?.id || ''}
                onChange={(e) => applyPreset('destination', e.target.value)}
                className="mt-1 w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">— choose or type coords —</option>
                {presets.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-2 mt-2">
                <input
                  type="number"
                  step="0.0001"
                  value={destination.lat}
                  onChange={(e) => setDestination({ ...destination, lat: parseFloat(e.target.value) || 0 })}
                  placeholder="Latitude"
                  className="px-3 py-1.5 border border-border rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <input
                  type="number"
                  step="0.0001"
                  value={destination.lng}
                  onChange={(e) => setDestination({ ...destination, lng: parseFloat(e.target.value) || 0 })}
                  placeholder="Longitude"
                  className="px-3 py-1.5 border border-border rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <button
              onClick={() => runPlan(origin, destination)}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-primary text-white text-sm font-semibold hover:bg-primary-dark transition-colors disabled:opacity-50"
            >
              {loading ? 'Planning…' : 'Plan Safe Route'}
            </button>

            {error && (
              <div className="p-3 rounded-xl bg-red-50 text-emergency text-xs font-medium">
                {error}
              </div>
            )}

            {!plan && !loading && !error && (
              <p className="text-xs text-text-secondary text-center py-2">
                Select an origin and destination, then plan a route.
              </p>
            )}
          </div>

          {plan && (
            <div className="space-y-3 border-t border-border pt-3">
              <div className="p-3 rounded-xl bg-background">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-text-secondary">Direct route</span>
                  <StatusBadge status={plan.direct.status} />
                </div>
                <p className="text-lg font-bold">{plan.direct.km.toFixed(1)} km</p>
                {plan.direct.danger_zones?.length > 0 && (
                  <div className="mt-2 space-y-1">
                    <p className="text-[10px] font-semibold uppercase text-text-secondary">Crosses</p>
                    {plan.direct.danger_zones.map((z) => (
                      <div key={z.id} className="flex items-center gap-1.5 text-xs" style={{ color: riskColors[z.risk] }}>
                        <AlertTriangle className="w-3 h-3" />
                        {z.name}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="p-3 rounded-xl bg-green-50 border border-green-100">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-text-secondary">Safe route</span>
                  <StatusBadge status={plan.recommended.status} />
                </div>
                <p className="text-lg font-bold text-success">{plan.recommended.km.toFixed(1)} km</p>
                {detourActive && (
                  <p className="text-xs text-warning font-medium">
                    {deltaKm > 0 ? `+${deltaKm.toFixed(1)} km longer` : 'Slightly shorter'} but clear of danger zones
                  </p>
                )}
                {plan.avoided_zones?.length > 0 && (
                  <div className="mt-2 space-y-1">
                    <p className="text-[10px] font-semibold uppercase text-text-secondary">Avoided areas</p>
                    {plan.avoided_zones.map((z) => (
                      <div key={z.id} className="flex items-center gap-1.5 text-xs" style={{ color: riskColors[z.risk] }}>
                        <MapPin className="w-3 h-3" />
                        {z.name}
                      </div>
                    ))}
                  </div>
                )}
                {plan.caution_zones?.length > 0 && (
                  <div className="mt-2 space-y-1">
                    <p className="text-[10px] font-semibold uppercase text-text-secondary">Caution (passable)</p>
                    {plan.caution_zones.map((z) => (
                      <div key={z.id} className="flex items-center gap-1.5 text-xs" style={{ color: riskColors[z.risk] }}>
                        <MapPin className="w-3 h-3" />
                        {z.name}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </aside>

        <div className="flex-1 relative min-h-[50vh]">
          <MapContainer
            center={[25.8, 92.6]}
            zoom={7}
            style={{ height: '100%', width: '100%' }}
            scrollWheelZoom={true}
          >
            <TileLayer attribution={MAP_ATTRIBUTION} url={MAP_TILE_URL} />
            <FitBounds points={plan ? buildPoints(plan) : []} />

            {zones.map((z) => (
              <CircleMarker
                key={z.id}
                center={[z.lat, z.lng]}
                radius={z.risk === 'red' ? 13 : z.risk === 'orange' ? 10 : z.risk === 'yellow' ? 8 : 6}
                pathOptions={{ fillColor: riskColors[z.risk], fillOpacity: 0.35, color: '#ffffff', weight: 1.5 }}
              >
                <Popup>
                  <div className="text-sm min-w-[150px]">
                    <p className="font-bold">{z.name}</p>
                    <p className="text-xs text-gray-500 mt-1">Risk: <span className="uppercase font-semibold" style={{ color: riskColors[z.risk] }}>{z.risk}</span></p>
                  </div>
                </Popup>
              </CircleMarker>
            ))}

            <CircleMarker
              center={[origin.lat, origin.lng]}
              radius={8}
              pathOptions={{ fillColor: '#3B82F6', fillOpacity: 1, color: '#fff', weight: 2 }}
            >
              <Popup>Origin</Popup>
            </CircleMarker>
            <CircleMarker
              center={[destination.lat, destination.lng]}
              radius={8}
              pathOptions={{ fillColor: '#1E293B', fillOpacity: 1, color: '#fff', weight: 2 }}
            >
              <Popup>Destination</Popup>
            </CircleMarker>

            {plan && (
              <>
                <Polyline
                  positions={plan.direct.path}
                  pathOptions={{
                    color: plan.direct.status === 'unsafe' ? '#DC2626' : '#9CA3AF',
                    weight: 3,
                    dashArray: '8 8',
                  }}
                />
                <Polyline
                  positions={plan.recommended.path}
                  pathOptions={{ color: '#16A34A', weight: 5, opacity: 0.9 }}
                />
                {plan.avoided_zones.map((z) => (
                  <CircleMarker
                    key={`av-${z.id}`}
                    center={[z.lat, z.lng]}
                    radius={11}
                    pathOptions={{ fillColor: riskColors[z.risk], fillOpacity: 0.85, color: '#fff', weight: 2 }}
                  >
                    <Popup>
                      <div className="text-sm">
                        <p className="font-bold">Avoided: {z.name}</p>
                        <p className="text-xs uppercase font-semibold mt-1" style={{ color: riskColors[z.risk] }}>{z.risk} risk</p>
                      </div>
                    </Popup>
                  </CircleMarker>
                ))}
              </>
            )}
          </MapContainer>

          <div className="absolute top-4 right-4 bg-white rounded-xl shadow-lg border border-border p-3 z-[1000]">
            <p className="text-xs font-semibold mb-2">Legend</p>
            <div className="space-y-1.5 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-4 h-0.5 bg-green-600" />
                <span>Safe route</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-0.5 bg-red-600" style={{ borderTop: '2px dashed #DC2626' }} />
                <span>Direct route</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500" />
                <span>Origin</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-gray-800" />
                <span>Destination</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}