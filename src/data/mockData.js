export const zones = [
  { id: 1, name: "Uttarakhand - Chamoli", lat: 30.4, lng: 79.3, risk: "red", rainfall: 142, slope: 45, swi: 0.12 },
  { id: 2, name: "Himachal - Kinnaur", lat: 31.6, lng: 78.3, risk: "orange", rainfall: 98, slope: 38, swi: 0.28 },
  { id: 3, name: "Kerala - Wayanad", lat: 11.8, lng: 76.1, risk: "red", rainfall: 187, slope: 32, swi: 0.08 },
  { id: 4, name: "Sikkim - North", lat: 27.5, lng: 88.5, risk: "yellow", rainfall: 76, slope: 41, swi: 0.35 },
  { id: 5, name: "Meghalaya - East", lat: 25.5, lng: 91.9, risk: "orange", rainfall: 124, slope: 29, swi: 0.22 },
  { id: 6, name: "Mahabaleshwar", lat: 17.9, lng: 73.6, risk: "yellow", rainfall: 89, slope: 26, swi: 0.31 },
  { id: 7, name: "Ooty - Nilgiris", lat: 11.4, lng: 76.7, risk: "green", rainfall: 54, slope: 22, swi: 0.52 },
  { id: 8, name: "Darjeeling", lat: 27.0, lng: 88.3, risk: "red", rainfall: 156, slope: 48, swi: 0.10 },
  { id: 9, name: "Munnar - Idukki", lat: 10.1, lng: 77.1, risk: "orange", rainfall: 112, slope: 35, swi: 0.19 },
  { id: 10, name: "Cherrapunji", lat: 25.3, lng: 91.7, risk: "yellow", rainfall: 95, slope: 30, swi: 0.38 },
];

export const alerts = [
  { id: "ALS-2401", zone: "Uttarakhand - Chamoli", type: "red", status: "delivered", time: "2 min ago", sms: 1240, recipients: 1580 },
  { id: "ALS-2400", zone: "Kerala - Wayanad", type: "red", status: "delivered", time: "18 min ago", sms: 980, recipients: 1120 },
  { id: "ALS-2399", zone: "Darjeeling", type: "orange", status: "acknowledged", time: "45 min ago", sms: 650, recipients: 780 },
  { id: "ALS-2398", zone: "Himachal - Kinnaur", type: "yellow", status: "delivered", time: "1 hr ago", sms: 430, recipients: 520 },
  { id: "ALS-2397", zone: "Meghalaya - East", type: "orange", status: "pending", time: "2 hr ago", sms: 310, recipients: 450 },
  { id: "ALS-2396", zone: "Sikkim - North", type: "yellow", status: "delivered", time: "3 hr ago", sms: 280, recipients: 340 },
  { id: "ALS-2395", zone: "Munnar - Idukki", type: "green", status: "acknowledged", time: "5 hr ago", sms: 150, recipients: 200 },
  { id: "ALS-2394", zone: "Mahabaleshwar", type: "yellow", status: "delivered", time: "6 hr ago", sms: 200, recipients: 260 },
];

export const rainfallData = [
  { time: "00:00", value: 12, forecast: 15 },
  { time: "03:00", value: 28, forecast: 30 },
  { time: "06:00", value: 45, forecast: 52 },
  { time: "09:00", value: 68, forecast: 75 },
  { time: "12:00", value: 92, forecast: 88 },
  { time: "15:00", value: 110, forecast: 105 },
  { time: "18:00", value: 85, forecast: 95 },
  { time: "21:00", value: 62, forecast: 70 },
  { time: "00:00+", value: null, forecast: 55 },
  { time: "03:00+", value: null, forecast: 42 },
];

export const swiTimeline = [
  { date: "Sep 1", swi: 0.52, risk: "green" },
  { date: "Sep 3", swi: 0.45, risk: "green" },
  { date: "Sep 5", swi: 0.38, risk: "yellow" },
  { date: "Sep 7", swi: 0.28, risk: "orange" },
  { date: "Sep 9", swi: 0.18, risk: "red" },
  { date: "Sep 10", swi: 0.12, risk: "red" },
];

export const systemHealth = [
  { name: "Rainfall API", status: "operational", uptime: "99.8%", latency: "42ms" },
  { name: "DEM Processing", status: "operational", uptime: "99.5%", latency: "120ms" },
  { name: "ML Prediction Model", status: "operational", uptime: "98.9%", latency: "850ms" },
  { name: "SMS Gateway", status: "degraded", uptime: "97.2%", latency: "1.2s" },
  { name: "PWA Push Service", status: "operational", uptime: "99.9%", latency: "35ms" },
  { name: "GIS Tile Server", status: "operational", uptime: "99.7%", latency: "95ms" },
];

export const stats = {
  zonesMonitored: 847,
  activeAlerts: 3,
  smsSentToday: 4230,
  livesAtRisk: 12400,
  rainfallStations: 1250,
  modelAccuracy: 94.2,
};
