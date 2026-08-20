/**
 * Search controls: location (manual or geolocation), radius, food type
 * autocomplete, free-text search, and search/reset actions.
 */

import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import { RADIUS_MAX_KM, RADIUS_MIN_KM } from '../config/env'

export interface SearchFormValues {
  lat: number
  lng: number
  radiusKm: number
  foodType: string
  search: string
}

interface SearchPanelProps {
  initial: SearchFormValues
  resetSignal: number
  locating: boolean
  foodOptions: string[]
  onUseMyLocation: () => void
  onSearch: (values: SearchFormValues) => void
  onReset: () => void
}

const RADIUS_OPTIONS = [0.5, 1, 2, 5, 10, 20, 50]

const POPULAR_SPOTS = [
  { name: 'Downtown / Union Square', lat: 37.7879, lng: -122.4075 },
  { name: 'Civic Center', lat: 37.7793, lng: -122.4193 },
  { name: 'Ferry Building', lat: 37.7955, lng: -122.3937 },
  { name: 'Mission District', lat: 37.7599, lng: -122.4148 },
  { name: "Fisherman's Wharf", lat: 37.808, lng: -122.4177 },
]

export function SearchPanel({
  initial,
  resetSignal,
  locating,
  foodOptions,
  onUseMyLocation,
  onSearch,
  onReset,
}: SearchPanelProps) {
  const [lat, setLat] = useState(String(initial.lat))
  const [lng, setLng] = useState(String(initial.lng))
  const [radiusKm, setRadiusKm] = useState(initial.radiusKm)
  const [foodType, setFoodType] = useState(initial.foodType)
  const [search, setSearch] = useState(initial.search)
  const [spot, setSpot] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  // Keep the location fields in sync when the query location changes
  // (e.g. after geolocation succeeds).
  useEffect(() => {
    setLat(String(initial.lat))
    setLng(String(initial.lng))
  }, [initial.lat, initial.lng])

  // Full form reset.
  useEffect(() => {
    setLat(String(initial.lat))
    setLng(String(initial.lng))
    setRadiusKm(initial.radiusKm)
    setFoodType(initial.foodType)
    setSearch(initial.search)
    setSpot('')
    setFormError(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetSignal])

  const handleSpotChange = (value: string) => {
    setSpot(value)
    const found = POPULAR_SPOTS.find((item) => item.name === value)
    if (found) {
      setLat(String(found.lat))
      setLng(String(found.lng))
      setFormError(null)
    }
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const parsedLat = Number(lat)
    const parsedLng = Number(lng)

    if (lat.trim() === '' || Number.isNaN(parsedLat) || parsedLat < -90 || parsedLat > 90) {
      setFormError('Latitude must be a number between -90 and 90.')
      return
    }
    if (lng.trim() === '' || Number.isNaN(parsedLng) || parsedLng < -180 || parsedLng > 180) {
      setFormError('Longitude must be a number between -180 and 180.')
      return
    }
    if (radiusKm < RADIUS_MIN_KM || radiusKm > RADIUS_MAX_KM) {
      setFormError(`Radius must be between ${RADIUS_MIN_KM} and ${RADIUS_MAX_KM} km.`)
      return
    }

    setFormError(null)
    onSearch({
      lat: parsedLat,
      lng: parsedLng,
      radiusKm,
      foodType: foodType.trim(),
      search: search.trim(),
    })
  }

  return (
    <form className="search-panel" onSubmit={handleSubmit} noValidate>
      <h2 className="search-panel__title">Find food trucks</h2>

      <div className="field-row">
        <div className="field">
          <label htmlFor="lat">Latitude</label>
          <input
            id="lat"
            type="number"
            step="any"
            inputMode="decimal"
            value={lat}
            onChange={(event) => setLat(event.target.value)}
            aria-describedby="location-hint"
          />
        </div>
        <div className="field">
          <label htmlFor="lng">Longitude</label>
          <input
            id="lng"
            type="number"
            step="any"
            inputMode="decimal"
            value={lng}
            onChange={(event) => setLng(event.target.value)}
          />
        </div>
      </div>
      <p id="location-hint" className="search-panel__hint">
        Use your current location, or pick a spot below.
      </p>

      <div className="field">
        <label htmlFor="spot">Popular spot</label>
        <select id="spot" value={spot} onChange={(event) => handleSpotChange(event.target.value)}>
          <option value="">Choose a San Francisco spot…</option>
          {POPULAR_SPOTS.map((item) => (
            <option key={item.name} value={item.name}>
              {item.name}
            </option>
          ))}
        </select>
      </div>

      <button
        type="button"
        className="btn btn--ghost btn--locate"
        onClick={onUseMyLocation}
        disabled={locating}
      >
        {locating ? 'Locating…' : 'Use my location'}
      </button>

      <div className="field">
        <label htmlFor="radius">Search radius</label>
        <select
          id="radius"
          value={String(radiusKm)}
          onChange={(event) => setRadiusKm(Number(event.target.value))}
        >
          {RADIUS_OPTIONS.map((km) => (
            <option key={km} value={km}>
              {km} km
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label htmlFor="food-type">Food type</label>
        <input
          id="food-type"
          list="food-type-options"
          placeholder="e.g. tacos"
          value={foodType}
          onChange={(event) => setFoodType(event.target.value)}
        />
        <datalist id="food-type-options">
          {foodOptions.map((option) => (
            <option key={option} value={option} />
          ))}
        </datalist>
      </div>

      <div className="field">
        <label htmlFor="search">Search</label>
        <input
          id="search"
          type="search"
          placeholder="Vendor, street, or food"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </div>

      {formError && (
        <p className="form-error" role="alert">
          {formError}
        </p>
      )}

      <div className="search-panel__actions">
        <button type="submit" className="btn">
          Search
        </button>
        <button type="button" className="btn btn--ghost" onClick={onReset}>
          Reset
        </button>
      </div>
    </form>
  )
}