import { HashRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Navbar from './components/Navbar';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import MapView from './pages/MapView';
import SOS from './pages/SOS';
import Alerts from './pages/Alerts';
import Login from './pages/Login';
import Admin from './pages/Admin';
import RoutesPage from './pages/Routes';

export default function App() {
  return (
    <AuthProvider>
      <HashRouter>
        <div className="min-h-screen bg-background">
          <Navbar />
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/map" element={<MapView />} />
            <Route path="/sos" element={<SOS />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/routes" element={<RoutesPage />} />
            <Route path="/login" element={<Login />} />
            <Route path="/admin" element={<Admin />} />
          </Routes>
        </div>
      </HashRouter>
    </AuthProvider>
  );
}
