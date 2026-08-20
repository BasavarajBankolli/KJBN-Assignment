/**
 * Environment-based frontend configuration.
 * Vite exposes only VITE_-prefixed variables to the browser bundle.
 */

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

/** Default search center: downtown San Francisco. */
export const DEFAULT_CENTER = { latitude: 37.7749, longitude: -122.4194 }

/** Default search radius in kilometers (matches backend default). */
export const DEFAULT_RADIUS_KM = 2

/** Backend-enforced bounds, mirrored here for early client-side feedback. */
export const RADIUS_MIN_KM = 0.1
export const RADIUS_MAX_KM = 50
export const LIMIT_MAX = 100