import { useEffect, useRef, useState } from 'react'

import { fetchFoodTrucks } from './api/client'
import { Header } from './components/Header'
import { MapView } from './components/MapView'
import { DEFAULT_CENTER, DEFAULT_RADIUS_KM, LIMIT_MAX } from './config/env'
import { useGeolocation } from './hooks/useGeolocation'
import type { Coordinates, FoodTruck } from './types/api'

export default function App() {
  const geolocation = useGeolocation()
  const [center, setCenter] = useState<Coordinates>(DEFAULT_CENTER)
  const [userLocation, setUserLocation] = useState<Coordinates | null>(null)
  const [locationNotice, setLocationNotice] = useState<string | null>(null)

  const [trucks, setTrucks] = useState<FoodTruck[]>([])
  const [loadingTrucks, setLoadingTrucks] = useState(false)
  const [truckError, setTruckError] = useState<string | null>(null)

  // Request geolocation once on startup (guarded against StrictMode double-fire).
  const autoRequested = useRef(false)
  useEffect(() => {
    if (autoRequested.current) return
    autoRequested.current = true
    geolocation.request()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // React to geolocation outcome: center on the user, or fall back to SF.
  useEffect(() => {
    if (geolocation.status === 'success' && geolocation.position) {
      setUserLocation(geolocation.position)
      setCenter(geolocation.position)
      setLocationNotice(null)
    } else if (geolocation.status === 'error' || geolocation.status === 'unsupported') {
      setUserLocation(null)
      setCenter(DEFAULT_CENTER)
      setLocationNotice(geolocation.error)
    }
  }, [geolocation.status, geolocation.position, geolocation.error])

  // Initial load of trucks for the current center.
  useEffect(() => {
    let cancelled = false
    setLoadingTrucks(true)
    setTruckError(null)

    fetchFoodTrucks({
      lat: center.latitude,
      lng: center.longitude,
      radiusKm: DEFAULT_RADIUS_KM,
      limit: LIMIT_MAX,
    })
      .then((data) => {
        if (!cancelled) setTrucks(data.trucks)
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setTrucks([])
          setTruckError(
            error instanceof Error ? error.message : 'Failed to load food trucks.',
          )
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingTrucks(false)
      })

    return () => {
      cancelled = true
    }
  }, [center.latitude, center.longitude])

  return (
    <div className="app-shell">
      <Header />
      <main className="app-main">
        <div className="map-stage">
          <MapView
            center={center}
            trucks={trucks}
            userLocation={userLocation}
          />

          {locationNotice && (
            <div className="location-banner" role="status">
              <span>{locationNotice}</span>
              <button type="button" className="btn btn--link" onClick={geolocation.request}>
                Try again
              </button>
            </div>
          )}

          <button
            type="button"
            className="btn locate-btn"
            onClick={geolocation.request}
            disabled={geolocation.status === 'loading'}
          >
            {geolocation.status === 'loading' ? 'Locating…' : 'Use my location'}
          </button>

          {loadingTrucks && (
            <div className="map-status" role="status">
              Loading nearby food trucks…
            </div>
          )}
          {!loadingTrucks && truckError && (
            <div className="map-status map-status--error" role="alert">
              {truckError}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}