/**
 * Typed API client for the Food Truck Finder backend.
 *
 * The frontend talks ONLY to our FastAPI backend - never to DataSF
 * directly. All requests funnel through this module.
 */

import {
  ApiRequestError,
  FoodTruckListResponse,
  FoodTruckSearchParams,
} from '../types/api'
import { API_BASE_URL } from '../config/env'

const BASE_URL = API_BASE_URL.replace(/\/+$/, '')
const PATH = `${BASE_URL}/api/v1/food-trucks`

function buildUrl(params: FoodTruckSearchParams): URL {
  const url = new URL(PATH, window.location.origin)
  url.searchParams.set('lat', String(params.lat))
  url.searchParams.set('lng', String(params.lng))
  if (params.radiusKm !== undefined) url.searchParams.set('radius', String(params.radiusKm))
  if (params.foodType) url.searchParams.set('food_type', params.foodType)
  if (params.search) url.searchParams.set('search', params.search)
  if (params.limit !== undefined) url.searchParams.set('limit', String(params.limit))
  if (params.offset !== undefined) url.searchParams.set('offset', String(params.offset))
  return url
}

async function parseError(response: Response): Promise<ApiRequestError> {
  let code = 'UNKNOWN_ERROR'
  let message = 'An unexpected error occurred.'
  try {
    const body = (await response.json()) as {
      error?: { code?: string; message?: string }
    }
    code = body.error?.code ?? code
    message = body.error?.message ?? message
  } catch {
    // Non-JSON error body - fall back to defaults.
  }
  return new ApiRequestError(code, message, response.status)
}

/** Search food trucks near a location. */
export async function fetchFoodTrucks(
  params: FoodTruckSearchParams,
): Promise<FoodTruckListResponse> {
  let response: Response
  try {
    response = await fetch(buildUrl(params))
  } catch {
    throw new ApiRequestError(
      'NETWORK_ERROR',
      'Could not reach the server. Please check your connection and try again.',
      0,
    )
  }

  if (!response.ok) {
    throw await parseError(response)
  }

  return (await response.json()) as FoodTruckListResponse
}