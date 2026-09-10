import { useState } from 'react';
import { AlertTriangle, Send, MapPin, CheckCircle, X } from 'lucide-react';
import { zones } from '../data/mockData';

export default function SOS() {
  const [selectedZone, setSelectedZone] = useState('');
  const [alertType, setAlertType] = useState('red');
  const [message, setMessage] = useState('');
  const [showConfirm, setShowConfirm] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSend = () => {
    setShowConfirm(false);
    setSent(true);
    setTimeout(() => setSent(false), 4000);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <div className="text-center mb-10">
        <div className="w-20 h-20 bg-emergency rounded-full flex items-center justify-center mx-auto mb-4 sos-pulse">
          <AlertTriangle className="w-10 h-10 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-emergency">Emergency SOS Alert</h1>
        <p className="text-text-secondary mt-2">Trigger an immediate landslide warning for affected communities</p>
      </div>

      {sent ? (
        <div className="bg-white rounded-2xl border border-border p-10 text-center slide-up">
          <CheckCircle className="w-16 h-16 text-success mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-success">Alert Sent Successfully!</h2>
          <p className="text-text-secondary mt-2">SMS and browser notifications are being delivered to the selected zone.</p>
          <div className="mt-6 p-4 bg-green-50 rounded-xl">
            <p className="text-sm font-medium text-success">Delivery Status</p>
            <div className="grid grid-cols-3 gap-4 mt-3">
              <div>
                <p className="text-2xl font-bold text-success">1,240</p>
                <p className="text-xs text-text-secondary">SMS Sent</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-primary">890</p>
                <p className="text-xs text-text-secondary">Push Delivered</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-warning">350</p>
                <p className="text-xs text-text-secondary">Pending</p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-border p-8">
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-semibold mb-2">Select Affected Zone</label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary" />
                <select
                  value={selectedZone}
                  onChange={(e) => setSelectedZone(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-border rounded-xl bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary appearance-none"
                >
                  <option value="">Choose a zone...</option>
                  {zones.map(zone => (
                    <option key={zone.id} value={zone.id}>
                      {zone.name} — Risk: {zone.risk.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold mb-2">Alert Level</label>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { value: 'yellow', label: 'Yellow', desc: 'Watch', color: 'bg-yellow-100 border-yellow-300 text-yellow-800' },
                  { value: 'orange', label: 'Orange', desc: 'Be Ready', color: 'bg-amber-100 border-amber-300 text-amber-800' },
                  { value: 'red', label: 'Red', desc: 'Evacuate', color: 'bg-red-100 border-red-300 text-red-800' },
                ].map(level => (
                  <button
                    key={level.value}
                    onClick={() => setAlertType(level.value)}
                    className={`p-4 rounded-xl border-2 text-center transition-all ${
                      alertType === level.value
                        ? `${level.color} border-current ring-2 ring-offset-2 ring-current`
                        : 'bg-white border-border hover:border-gray-300'
                    }`}
                  >
                    <p className="font-bold text-lg">{level.label}</p>
                    <p className="text-xs mt-1 opacity-80">{level.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold mb-2">Additional Message (optional)</label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="e.g., Heavy rainfall expected. Evacuate immediately via Route 7..."
                rows={3}
                className="w-full px-4 py-3 border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              />
            </div>

            <button
              onClick={() => selectedZone && setShowConfirm(true)}
              disabled={!selectedZone}
              className="w-full py-4 bg-emergency text-white font-bold text-lg rounded-xl flex items-center justify-center gap-3 transition-all hover:bg-emergency-dark disabled:opacity-40 disabled:cursor-not-allowed sos-pulse"
            >
              <Send className="w-5 h-5" />
              SEND SOS ALERT
            </button>
          </div>
        </div>
      )}

      {showConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full slide-up">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold">Confirm SOS Alert</h3>
              <button onClick={() => setShowConfirm(false)} className="p-1 hover:bg-gray-100 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 bg-red-50 rounded-xl mb-4">
              <p className="text-sm">
                You are about to send a <strong className="text-emergency uppercase">{alertType}</strong> level alert to
                <strong> {zones.find(z => z.id === Number(selectedZone))?.name}</strong>.
              </p>
              <p className="text-sm mt-2 text-text-secondary">
                This will trigger SMS notifications to all registered users in the zone and browser push alerts for PWA users.
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 py-2.5 border border-border rounded-xl text-sm font-medium hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSend}
                className="flex-1 py-2.5 bg-emergency text-white rounded-xl text-sm font-bold hover:bg-emergency-dark"
              >
                Confirm & Send
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
