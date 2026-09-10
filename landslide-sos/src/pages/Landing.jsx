import { Link } from 'react-router-dom';
import { Mountain, Shield, Radio, MapPin, AlertTriangle, BarChart3, Smartphone, ArrowRight, Zap } from 'lucide-react';
import { stats } from '../data/mockData';

export default function Landing() {
  const features = [
    { icon: Radio, title: "Real-Time Rainfall", desc: "Near real-time rainfall observations and short-term forecasts across India" },
    { icon: Mountain, title: "Terrain Analysis", desc: "Digital elevation models for slope, aspect, and terrain risk assessment" },
    { icon: MapPin, title: "Interactive GIS Map", desc: "Heatmaps, custom layers, and animated SWI movement tracking" },
    { icon: AlertTriangle, title: "SOS Alerts", desc: "Automated SMS and browser-based alerts for Yellow, Orange, and Red zones" },
    { icon: Smartphone, title: "Offline PWA", desc: "Mobile-friendly interface that works offline for critical alert delivery" },
    { icon: BarChart3, title: "Admin Dashboard", desc: "System health monitoring, model performance, and role-based access" },
  ];

  return (
    <div className="min-h-screen">
      <section className="relative bg-gradient-to-br from-primary via-primary-dark to-blue-900 text-white overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 left-10 w-72 h-72 bg-white rounded-full blur-3xl" />
          <div className="absolute bottom-10 right-20 w-96 h-96 bg-blue-300 rounded-full blur-3xl" />
        </div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 md:py-32 relative">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-12 h-12 bg-white/20 backdrop-blur rounded-xl flex items-center justify-center">
              <Mountain className="w-7 h-7" />
            </div>
            <span className="text-xl font-bold">LandslideSOS</span>
          </div>
          <h1 className="text-4xl md:text-6xl font-bold leading-tight max-w-3xl">
            India Landslide Early Warning & SOS System
          </h1>
          <p className="text-blue-100 text-lg md:text-xl mt-6 max-w-2xl leading-relaxed">
            AI-powered landslide prediction with real-time monitoring, automated alerts,
            and community-driven disaster response for India's mountainous regions.
          </p>
          <div className="flex flex-wrap gap-4 mt-10">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 px-6 py-3 bg-white text-primary font-semibold rounded-xl no-underline hover:bg-blue-50 transition-colors"
            >
              <Zap className="w-5 h-5" />
              Open Dashboard
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/sos"
              className="inline-flex items-center gap-2 px-6 py-3 bg-emergency text-white font-semibold rounded-xl no-underline hover:bg-emergency-dark transition-colors sos-pulse"
            >
              <AlertTriangle className="w-5 h-5" />
              Trigger SOS
            </Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-16 pt-10 border-t border-white/20">
            <div>
              <p className="text-3xl font-bold">{stats.zonesMonitored}+</p>
              <p className="text-blue-200 text-sm mt-1">Zones Monitored</p>
            </div>
            <div>
              <p className="text-3xl font-bold">{stats.rainfallStations.toLocaleString()}</p>
              <p className="text-blue-200 text-sm mt-1">Rainfall Stations</p>
            </div>
            <div>
              <p className="text-3xl font-bold">{stats.smsSentToday.toLocaleString()}</p>
              <p className="text-blue-200 text-sm mt-1">Alerts Sent Today</p>
            </div>
            <div>
              <p className="text-3xl font-bold">{stats.modelAccuracy}%</p>
              <p className="text-blue-200 text-sm mt-1">Model Accuracy</p>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center mb-14">
          <p className="text-primary font-semibold text-sm uppercase tracking-wider">Platform Features</p>
          <h2 className="text-3xl md:text-4xl font-bold mt-3">Complete Landslide Monitoring Suite</h2>
          <p className="text-text-secondary mt-4 max-w-2xl mx-auto">
            From real-time data collection to automated emergency alerts, everything you need to protect communities.
          </p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <div key={i} className="bg-white rounded-2xl border border-border p-6 hover:shadow-lg transition-all hover:-translate-y-1">
              <div className="w-12 h-12 bg-primary-light rounded-xl flex items-center justify-center mb-4">
                <f.icon className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-bold text-lg">{f.title}</h3>
              <p className="text-text-secondary text-sm mt-2 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white border-t border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
          <h2 className="text-2xl md:text-3xl font-bold">Built for Disaster Response Teams</h2>
          <p className="text-text-secondary mt-3 max-w-xl mx-auto">
            Multi-role access for administrators, field officers, and public users.
            Every second counts in a disaster.
          </p>
          <div className="flex flex-wrap justify-center gap-4 mt-8">
            {['Admin Panel', 'Field Officer Dashboard', 'Public Alert Portal'].map((role, i) => (
              <div key={i} className="px-5 py-3 bg-background rounded-xl border border-border text-sm font-medium">
                <Shield className="w-4 h-4 inline mr-2 text-primary" />
                {role}
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="bg-slate-900 text-slate-400 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Mountain className="w-5 h-5 text-primary" />
            <span className="font-semibold text-white">LandslideSOS</span>
            <span className="text-sm">— Smart India Hackathon 2026</span>
          </div>
          <p className="text-sm">Ministry of Earth Sciences | NDMA | Government of India</p>
        </div>
      </footer>
    </div>
  );
}
