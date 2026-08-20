/**
 * TypeScript models mirroring the backend API contract (app/schemas/api.py).
 * Keep in sync with the backend response schemas.
 */

export interface Coordinates {
  latitude: number
  longitude: number
}

export interface FoodTruck {
  id: string
  applicant: string
  facility_type: string | null
  location_description: string | null
  address: string | null
  food_items: string | null
  latitude: number
  longitude: number
  distance_m: number
}

export interface FoodTruckListResponse {
  trucks: FoodTruck[]
  total: number
  limit: number
  offset: number
  center: Coordinates
  radius_km: number
}

export interface FoodTruckSearchParams {
  lat: number
  lng: number
  radiusKm?: number
  foodType?: string
  search?: string
  limit?: number
  offset?: number
}

export interface ApiErrorEnvelope {
  error: {
    code: string
    message: string
  }
}

/** Error raised by the API client for both network and API-level failures. */
export class ApiRequestError extends Error {
  readonly code: string
  readonly status: number

  constructor(code: string, message: string, status: number) {
    super(message)
    this.name = 'ApiRequestError'
    this.code = code
    this.status = status
  }
}