import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { fetchFoodTrucks } from './api/client'
import { Header } from './components/Header'
import { MapView, type MapViewHandle } from './components/MapView'
import { SearchPanel, type SearchFormValues } from './components/SearchPanel'
import { TruckList } from './components/TruckList'
import { DEFAULT_CENTER, DEFAULT_RADIUS_KM, LIMIT_MAX } from './config/env'
import { useGeolocation } from './hooks/useGeolocation'
import type { Coordinates, FoodTruck } from './types/api'

const DEFAULT_QUERY: SearchFormValues = {
  lat: DEFAULT_CENTER.latitude,
  lng: DEFAULT_CENTER.longitude,
  radiusKm: DEFAULT_RADIUS_KM,
  foodType: '',
  search: '',
}

export default function App() {
  const geolocation = useGeolocation()

  // Submitted search query (drives the fetch and the map center).
  const [query, setQuery] = useState<SearchFormValues>(DEFAULT_QUERY)
  const [userLocation, setUserLocation] = useState<Coordinates | null>(null)
  const [locationNotice, setLocationNotice] = useState<string | null>(null)

  const [trucks, setTrucks] = useState<FoodTruck[]>([])
  const [total, setTotal] = useState(0)
  const [loadingTrucks, setLoadingTrucks] = useState(false)
  const [truckError, setTruckError] = useState<string | null>(null)
  const [selectedTruckId, setSelectedTruckId] = useState<string | null>(null)

  const [reloadToken, setReloadToken] = useState(0)
  const [resetSignal, setResetSignal] = useState(0)
  const mapRef = useRef<MapViewHandle>(null)

  // Request geolocation once on startup (guarded against StrictMode double-fire).
  const autoRequested = useRef(false)
  useEffect(() => {
    if (autoRequested.current) return
    autoRequested.current = true
    geolocation.request()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // React to geolocation outcome: search from the user's position, or
  // show a graceful fallback notice.
  useEffect(() => {
    if (geolocation.status === 'success' && geolocation.position) {
      setUserLocation(geolocation.position)
      setLocationNotice(null)
      setQuery((current) => ({
        ...current,
        lat: geolocation.position!.latitude,
        lng: geolocation.position!.longitude,
      }))
    } else if (geolocation.status === 'error' || geolocation.status === 'unsupported') {
      setUserLocation(null)
      setLocationNotice(geolocation.error)
    }
  }, [geolocation.status, geolocation.position, geolocation.error])

  // Fetch results whenever the query or a manual retry changes.
  useEffect(() => {
    let cancelled = false
    setLoadingTrucks(true)
    setTruckError(null)

    fetchFoodTrucks({
      lat: query.lat,
      lng: query.lng,
      radiusKm: query.radiusKm,
      foodType: query.foodType || undefined,
      search: query.search || undefined,
      limit: LIMIT_MAX,
    })
      .then((data) => {
        if (cancelled) return
        setTrucks(data.trucks)
        setTotal(data.total)
        setSelectedTruckId(null)
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setTrucks([])
        setTotal(0)
        setTruckError(error instanceof Error ? error.message : 'Failed to load food trucks.')
      })
      .finally(() => {
        if (!cancelled) setLoadingTrucks(false)
      })

    return () => {
      cancelled = true
    }
  }, [query, reloadToken])

  // Distinct food keywords from the current results, for autocomplete.
  const foodOptions = useMemo(() => {
    const seen = new Set<string>()
    const options: string[] = []
    for (const truck of trucks) {
      for (const token of (truck.food_items ?? '').split(/[:;,]/)) {
        const clean = token.trim().toLowerCase()
        if (clean && !seen.has(clean)) {
          seen.add(clean)
          options.push(clean)
        }
      }
    }
    return options.slice(0, 50)
  }, [trucks])

  const handleReset = useCallback(() => {
    setQuery(DEFAULT_QUERY)
    setSelectedTruckId(null)
    setResetSignal((signal) => signal + 1)
  }, [])

  // Result card clicked -> highlight card and focus its marker.
  const handleSelectFromList = useCallback((truck: FoodTruck) => {
    setSelectedTruckId(truck.id)
    mapRef.current?.focusTruck(truck)
  }, [])

  // Marker clicked -> identify and highlight the corresponding result.
  const handleSelectFromMarker = useCallback((truck: FoodTruck) => {
    setSelectedTruckId(truck.id)
  }, [])

  return (
    <div className="app-shell">
      <Header />
      <main className="app-main">
        <aside className="sidebar">
          <SearchPanel
            initial={query}
            resetSignal={resetSignal}
            locating={geolocation.status === 'loading'}
            foodOptions={foodOptions}
            onUseMyLocation={geolocation.request}
            onSearch={(values) => {
              setQuery(values)
              setSelectedTruckId(null)
            }}
            onReset={handleReset}
          />
          <TruckList
            trucks={trucks}
            total={total}
            radiusKm={query.radiusKm}
            loading={loadingTrucks}
            error={truckError}
            selectedId={selectedTruckId}
            onSelect={handleSelectFromList}
            onRetry={() => setReloadToken((token) => token + 1)}
          />
        </aside>

        <div className="map-stage">
          <MapView
            ref={mapRef}
            center={{ latitude: query.lat, longitude: query.lng }}
            trucks={trucks}
            userLocation={userLocation}
            selectedTruckId={selectedTruckId}
            onSelectTruck={handleSelectFromMarker}
          />

          {locationNotice && (
            <div className="location-banner" role="status">
              <span>{locationNotice}</span>
              <button type="button" className="btn btn--link" onClick={geolocation.request}>
                Try again
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}