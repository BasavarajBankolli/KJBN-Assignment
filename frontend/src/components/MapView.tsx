/**
 * Interactive Leaflet map for food truck results.
 *
 * Pure presentation: given a center, truck list, and optional user
 * location, it renders markers, popups, and the user's position.
 * All data comes from props - no fetching happens here.
 */

import { useEffect } from 'react'
import L from 'leaflet'
import {
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
} from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

import type { Coordinates, FoodTruck } from '../types/api'

const OSM_TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

/** Recenter the map (with animation) whenever the center prop changes. */
function FlyToCenter({ center }: { center: Coordinates }) {
  const map = useMap()

  useEffect(() => {
    map.flyTo([center.latitude, center.longitude], map.getZoom(), { duration: 0.8 })
  }, [map, center.latitude, center.longitude])

  return null
}

function createTruckIcon() {
  return L.divIcon({
    className: 'truck-marker',
    html: '<div class="truck-pin" aria-hidden="true"></div>',
    iconSize: [28, 38],
    iconAnchor: [14, 36],
    popupAnchor: [0, -32],
  })
}

function createUserIcon() {
  return L.divIcon({
    className: 'user-marker',
    html: '<div class="user-dot" aria-hidden="true"></div>',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  })
}

interface MapViewProps {
  center: Coordinates
  trucks: FoodTruck[]
  userLocation: Coordinates | null
  onSelectTruck?: (truck: FoodTruck) => void
}

export function MapView({ center, trucks, userLocation, onSelectTruck }: MapViewProps) {
  return (
    <MapContainer
      center={[center.latitude, center.longitude]}
      zoom={14}
      className="map-container"
    >
      <TileLayer attribution={OSM_ATTRIBUTION} url={OSM_TILE_URL} />
      <FlyToCenter center={center} />

      {trucks.map((truck) => (
        <Marker
          key={truck.id}
          position={[truck.latitude, truck.longitude]}
          icon={createTruckIcon()}
          eventHandlers={{ click: () => onSelectTruck?.(truck) }}
        >
          <Popup>
            <div className="truck-popup">
              <strong className="truck-popup__name">{truck.applicant}</strong>
              {truck.food_items && (
                <span className="truck-popup__food">{truck.food_items}</span>
              )}
              {truck.address && <span className="truck-popup__address">{truck.address}</span>}
              <span className="truck-popup__distance">
                {Math.round(truck.distance_m)} m from center
              </span>
            </div>
          </Popup>
        </Marker>
      ))}

      {userLocation && (
        <Marker
          position={[userLocation.latitude, userLocation.longitude]}
          icon={createUserIcon()}
          zIndexOffset={1000}
        >
          <Popup>You are here</Popup>
        </Marker>
      )}
    </MapContainer>
  )
}