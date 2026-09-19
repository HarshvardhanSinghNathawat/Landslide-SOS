const mapboxToken = import.meta.env.VITE_MAPBOX_TOKEN;

export const MAP_TILE_URL = mapboxToken
  ? `https://api.mapbox.com/styles/v1/mapbox/standard/tiles/{z}/{x}/{y}?access_token=${mapboxToken}`
  : 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

export const MAP_ATTRIBUTION = mapboxToken
  ? '&copy; <a href="https://www.mapbox.com/about/maps/">Mapbox</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';