/**
 * Interactive Leaflet map for food truck results.
 *
 * Presentation component: given a center, truck list, and optional user
 * location, it renders markers, popups, and the user's position.
 *
 * Synchronization with the result list:
 * - clicking a marker reports the truck via `onSelectTruck`;
 * - the parent can focus a truck's marker imperatively through the
 *   `MapViewHandle` exposed via ref (fly-to + open popup).
 */

import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
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

/** Bridges the Leaflet map instance out to MapView's ref for imperative use. */
function MapBridge({ mapRef }: { mapRef: React.MutableRefObject<L.Map | null> }) {
  const map = useMap()

  useEffect(() => {
    mapRef.current = map
    return () => {
      mapRef.current = null
    }
  }, [map, mapRef])

  return null
}

function createTruckIcon(selected: boolean) {
  return L.divIcon({
    className: 'truck-marker',
    html: `<div class="truck-pin${selected ? ' truck-pin--selected' : ''}" aria-hidden="true"></div>`,
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

export interface MapViewHandle {
  /** Fly to the truck's marker and open its popup. */
  focusTruck: (truck: FoodTruck) => void
}

interface MapViewProps {
  center: Coordinates
  trucks: FoodTruck[]
  userLocation: Coordinates | null
  selectedTruckId: string | null
  onSelectTruck?: (truck: FoodTruck) => void
}

export const MapView = forwardRef<MapViewHandle, MapViewProps>(function MapView(
  { center, trucks, userLocation, selectedTruckId, onSelectTruck },
  ref,
) {
  const mapRef = useRef<L.Map | null>(null)
  const markerRefs = useRef<Record<string, L.Marker>>({})

  useImperativeHandle(ref, () => ({
    focusTruck: (truck: FoodTruck) => {
      const map = mapRef.current
      const marker = markerRefs.current[truck.id]
      if (!map || !marker) return
      map.flyTo([truck.latitude, truck.longitude], Math.max(map.getZoom(), 16), {
        duration: 0.7,
      })
      marker.openPopup()
    },
  }))

  return (
    <MapContainer
      center={[center.latitude, center.longitude]}
      zoom={14}
      className="map-container"
    >
      <MapBridge mapRef={mapRef} />
      <TileLayer attribution={OSM_ATTRIBUTION} url={OSM_TILE_URL} />
      <FlyToCenter center={center} />

      {trucks.map((truck) => (
        <Marker
          key={truck.id}
          position={[truck.latitude, truck.longitude]}
          icon={createTruckIcon(selectedTruckId === truck.id)}
          ref={(instance) => {
            if (instance) markerRefs.current[truck.id] = instance
            else delete markerRefs.current[truck.id]
          }}
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
})