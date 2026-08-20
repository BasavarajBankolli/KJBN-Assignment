/**
 * Browser geolocation hook.
 *
 * Handles the full life cycle of asking for the user's location:
 * success, denial, error, and unsupported browsers. The user can
 * re-request location at any time via the returned `request` function.
 */

import { useCallback, useState } from 'react'

export type GeolocationStatus = 'idle' | 'loading' | 'success' | 'error' | 'unsupported'

export interface UserPosition {
  latitude: number
  longitude: number
}

interface GeolocationState {
  status: GeolocationStatus
  position: UserPosition | null
  error: string | null
}

export function useGeolocation(options?: PositionOptions) {
  const [state, setState] = useState<GeolocationState>({
    status: 'idle',
    position: null,
    error: null,
  })

  const request = useCallback(() => {
    if (!('geolocation' in navigator)) {
      setState({
        status: 'unsupported',
        position: null,
        error: 'Geolocation is not supported by this browser.',
      })
      return
    }

    setState({ status: 'loading', position: null, error: null })

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setState({
          status: 'success',
          position: {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          },
          error: null,
        })
      },
      (error) => {
        const message =
          error.code === error.PERMISSION_DENIED
            ? 'Location permission was denied. You can still search using a manual location.'
            : 'Could not determine your location. You can still search using a manual location.'
        setState({ status: 'error', position: null, error: message })
      },
      options,
    )
  }, [])

  return { ...state, request }
}