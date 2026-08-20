/**
 * Food truck result list: summary, cards, and loading/error/empty states.
 * Clicking a card focuses its marker on the map (handled by the parent
 * via `onSelect` + the map ref).
 */

import { useEffect, useRef } from 'react'

import type { FoodTruck } from '../types/api'

interface TruckListProps {
  trucks: FoodTruck[]
  total: number
  radiusKm: number
  loading: boolean
  error: string | null
  selectedId: string | null
  onSelect: (truck: FoodTruck) => void
  onRetry: () => void
}

export function TruckList({
  trucks,
  total,
  radiusKm,
  loading,
  error,
  selectedId,
  onSelect,
  onRetry,
}: TruckListProps) {
  const cardRefs = useRef<Record<string, HTMLElement | null>>({})

  // Keep the selected card in view (e.g. after clicking its marker).
  useEffect(() => {
    if (!selectedId) return
    cardRefs.current[selectedId]?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [selectedId])

  if (loading) {
    return (
      <div className="truck-list" role="status">
        <p className="state-note">Searching for food trucks…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="truck-list" role="alert">
        <p className="state-note state-note--error">{error}</p>
        <button type="button" className="btn" onClick={onRetry}>
          Retry
        </button>
      </div>
    )
  }

  if (trucks.length === 0) {
    return (
      <div className="truck-list">
        <p className="state-note">
          No food trucks found within {radiusKm} km. Try a larger radius or different
          filters.
        </p>
      </div>
    )
  }

  return (
    <div className="truck-list">
      <p className="truck-list__summary" role="status">
        {total} {total === 1 ? 'truck' : 'trucks'} found within {radiusKm} km
      </p>
      <ul className="truck-list__items">
        {trucks.map((truck) => (
          <li key={truck.id}>
            <button
              type="button"
              className={
                selectedId === truck.id ? 'truck-card truck-card--selected' : 'truck-card'
              }
              onClick={() => onSelect(truck)}
              ref={(element) => {
                cardRefs.current[truck.id] = element
              }}
            >
              <span className="truck-card__name">{truck.applicant}</span>
              {truck.food_items && <span className="truck-card__food">{truck.food_items}</span>}
              {truck.address && <span className="truck-card__address">{truck.address}</span>}
              <span className="truck-card__distance">{Math.round(truck.distance_m)} m</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}