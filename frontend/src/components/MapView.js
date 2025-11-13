import React, { useRef, useEffect } from 'react';
import { MapContainer, TileLayer, FeatureGroup, GeoJSON, Marker, Popup } from 'react-leaflet';
import { EditControl } from 'react-leaflet-draw';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';

// Fix for default marker icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const colors = [
  '#3388ff', '#ff3388', '#33ff88', '#ff8833', '#8833ff', '#33ffff', '#ff33ff'
];

function MapView({ onPolygonCreated, segments }) {
  const mapRef = useRef();
  const featureGroupRef = useRef();

  const center = [37.7749, -122.4194]; // Default: San Francisco
  const zoom = 13;

  const handleCreated = (e) => {
    const layer = e.layer;
    const geoJSON = layer.toGeoJSON();

    // Convert to GeoJSON geometry
    onPolygonCreated(geoJSON.geometry);
  };

  const handleEdited = (e) => {
    const layers = e.layers;
    layers.eachLayer((layer) => {
      const geoJSON = layer.toGeoJSON();
      onPolygonCreated(geoJSON.geometry);
    });
  };

  const getSegmentStyle = (feature) => {
    const colorIndex = (feature.properties.sequence - 1) % colors.length;
    return {
      fillColor: colors[colorIndex],
      fillOpacity: 0.3,
      color: '#000000',
      weight: 2
    };
  };

  const onEachSegment = (feature, layer) => {
    if (feature.properties) {
      const props = feature.properties;
      layer.bindPopup(`
        <div>
          <h3>Segment ${props.sequence}</h3>
          <p><strong>Area:</strong> ${props.area_acres?.toFixed(2)} acres</p>
          <p><strong>Access:</strong> ${props.access_type}</p>
          <p><strong>Launch Point:</strong></p>
          <p>Lat: ${props.launch_point?.coordinates?.[1]?.toFixed(6)}</p>
          <p>Lon: ${props.launch_point?.coordinates?.[0]?.toFixed(6)}</p>
        </div>
      `);
    }
  };

  // Zoom to segments when loaded
  useEffect(() => {
    if (segments && segments.features && segments.features.length > 0 && mapRef.current) {
      const bounds = L.geoJSON(segments).getBounds();
      mapRef.current.fitBounds(bounds);
    }
  }, [segments]);

  return (
    <MapContainer
      center={center}
      zoom={zoom}
      style={{ height: '100%', width: '100%' }}
      ref={mapRef}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Drawing Controls */}
      <FeatureGroup ref={featureGroupRef}>
        <EditControl
          position="topright"
          onCreated={handleCreated}
          onEdited={handleEdited}
          draw={{
            rectangle: false,
            circle: false,
            circlemarker: false,
            marker: false,
            polyline: false,
            polygon: {
              allowIntersection: false,
              showArea: true,
              metric: ['km', 'm']
            }
          }}
        />
      </FeatureGroup>

      {/* Display Segments */}
      {segments && (
        <GeoJSON
          data={segments}
          style={getSegmentStyle}
          onEachFeature={onEachSegment}
        />
      )}

      {/* Display Launch Points */}
      {segments && segments.features && segments.features.map((feature, idx) => {
        const coords = feature.properties.launch_point?.coordinates;
        if (coords) {
          return (
            <Marker key={idx} position={[coords[1], coords[0]]}>
              <Popup>
                <div>
                  <h4>Launch Point {feature.properties.sequence}</h4>
                  <p>Segment {feature.properties.sequence}</p>
                </div>
              </Popup>
            </Marker>
          );
        }
        return null;
      })}
    </MapContainer>
  );
}

export default MapView;
