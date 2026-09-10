import { useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { Eye, EyeOff, Clock } from 'lucide-react';
import AlertBadge from '../components/AlertBadge';
import { zones, swiTimeline } from '../data/mockData';

const riskColors = { red: '#DC2626', orange: '#F59E0B', yellow: '#EAB308', green: '#16A34A' };

export default function MapView() {
  const [showRainfall, setShowRainfall] = useState(true);
  const [showSlope, setShowSlope] = useState(false);
  const [showAlerts, setShowAlerts] = useState(true);
  const [timelineIdx, setTimelineIdx] = useState(swiTimeline.length - 1);
  const currentSWI = swiTimeline[timelineIdx];

  const rainfallCircles = [
    { lat: 30.4, lng: 79.3, intensity: 142 },
    { lat: 27.0, lng: 88.3, intensity: 156 },
    { lat: 11.8, lng: 76.1, intensity: 187 },
    { lat: 25.5, lng: 91.9, intensity: 124 },
    { lat: 10.1, lng: 77.1, intensity: 112 },
  ];

  const slopeCircles = [
    { lat: 30.4, lng: 79.3, slope: 45 },
    { lat: 31.6, lng: 78.3, slope: 38 },
    { lat: 27.0, lng: 88.3, slope: 48 },
    { lat: 27.5, lng: 88.5, slope: 41 },
  ];

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <div className="bg-white border-b border-border px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-semibold text-lg">GIS Map View</h1>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setShowRainfall(!showRainfall)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              showRainfall ? 'bg-blue-50 border-blue-200 text-blue-700' : 'bg-white border-border text-text-secondary'
            }`}
          >
            {showRainfall ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            Rainfall Heatmap
          </button>
          <button
            onClick={() => setShowSlope(!showSlope)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              showSlope ? 'bg-amber-50 border-amber-200 text-amber-700' : 'bg-white border-border text-text-secondary'
            }`}
          >
            {showSlope ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            Slope/DEM
          </button>
          <button
            onClick={() => setShowAlerts(!showAlerts)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              showAlerts ? 'bg-red-50 border-red-200 text-red-700' : 'bg-white border-border text-text-secondary'
            }`}
          >
            {showAlerts ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            Active Alerts
          </button>
        </div>
      </div>

      <div className="flex-1 relative">
        <MapContainer
          center={[22.5, 82]}
          zoom={5}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {showAlerts && zones.map(zone => (
            <CircleMarker
              key={zone.id}
              center={[zone.lat, zone.lng]}
              radius={zone.risk === 'red' ? 14 : zone.risk === 'orange' ? 11 : 9}
              fillColor={riskColors[zone.risk]}
              fillOpacity={0.7}
              color="white"
              weight={2}
            >
              <Popup>
                <div className="text-sm min-w-[160px]">
                  <p className="font-bold text-base">{zone.name}</p>
                  <div className="mt-2 space-y-1">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Risk Level:</span>
                      <span className="uppercase font-semibold" style={{ color: riskColors[zone.risk] }}>{zone.risk}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Rainfall:</span>
                      <span>{zone.rainfall} mm</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Slope:</span>
                      <span>{zone.slope}°</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">SWI Index:</span>
                      <span className="font-mono">{zone.swi}</span>
                    </div>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          ))}

          {showRainfall && rainfallCircles.map((c, i) => (
            <CircleMarker
              key={`rain-${i}`}
              center={[c.lat, c.lng]}
              radius={c.intensity / 10}
              fillColor="#3B82F6"
              fillOpacity={0.25}
              color="#3B82F6"
              weight={1}
              dashArray="4 4"
            />
          ))}

          {showSlope && slopeCircles.map((c, i) => (
            <CircleMarker
              key={`slope-${i}`}
              center={[c.lat, c.lng]}
              radius={c.slope / 3}
              fillColor="#F59E0B"
              fillOpacity={0.2}
              color="#F59E0B"
              weight={1}
              dashArray="4 4"
            />
          ))}
        </MapContainer>

        <div className="absolute bottom-4 left-4 right-4 bg-white rounded-xl shadow-lg border border-border p-4 z-[1000]">
          <div className="flex items-center gap-3 mb-2">
            <Clock className="w-4 h-4 text-primary" />
            <span className="text-sm font-semibold">SWI Timeline Animation</span>
            <span className="text-xs text-text-secondary ml-auto">{currentSWI.date}</span>
          </div>
          <input
            type="range"
            min={0}
            max={swiTimeline.length - 1}
            value={timelineIdx}
            onChange={(e) => setTimelineIdx(parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary"
          />
          <div className="flex justify-between mt-1">
            {swiTimeline.map((t, i) => (
              <span key={i} className={`text-[10px] ${i === timelineIdx ? 'text-primary font-bold' : 'text-text-secondary'}`}>
                {t.date}
              </span>
            ))}
          </div>
          <div className="flex items-center gap-4 mt-3 pt-3 border-t border-border">
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-secondary">Current SWI:</span>
              <span className="text-sm font-bold font-mono" style={{ color: riskColors[currentSWI.risk] }}>{currentSWI.swi}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-secondary">Risk:</span>
              <AlertBadge type={currentSWI.risk} size="sm" />
            </div>
          </div>
        </div>

        <div className="absolute top-4 right-4 bg-white rounded-xl shadow-lg border border-border p-3 z-[1000]">
          <p className="text-xs font-semibold mb-2">Legend</p>
          <div className="space-y-1.5">
            {Object.entries(riskColors).map(([level, color]) => (
              <div key={level} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ background: color }} />
                <span className="text-xs capitalize">{level} Risk</span>
              </div>
            ))}
            <div className="border-t border-border pt-1.5 mt-1.5">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500 opacity-30" />
                <span className="text-xs">Rainfall Zone</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-amber-500 opacity-30" />
                <span className="text-xs">Slope Zone</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
