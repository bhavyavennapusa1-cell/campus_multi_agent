import os
import httpx
from typing import Dict, Any, Optional


class GoogleMapsAdapter:
    """
    Adapter for Google Maps Directions & Places APIs.
    Used for off-campus routing or external facility lookups where campus DB does not cover.
    Campus DB remains the primary source of truth for on-campus indoor wayfinding & buildings.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")

    async def get_directions(self, origin: str, destination: str, mode: str = "walking") -> Dict[str, Any]:
        if self.api_key:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        "https://maps.googleapis.com/maps/api/directions/json",
                        params={"origin": origin, "destination": destination, "mode": mode, "key": self.api_key}
                    )
                    if resp.status_code == 200 and resp.json().get("status") == "OK":
                        route = resp.json()["routes"][0]["legs"][0]
                        return {
                            "source": "live",
                            "origin": origin,
                            "destination": destination,
                            "distance": route["distance"]["text"],
                            "duration": route["duration"]["text"],
                            "steps": [s["html_instructions"].replace("<b>", "").replace("</b>", "") for s in route["steps"]]
                        }
            except Exception as exc:
                print(f"[GoogleMapsAdapter] Live API call failed ({exc}). Falling back to mock response.")

        # Fallback Mock Data
        return {
            "source": "mock",
            "origin": origin,
            "destination": destination,
            "distance_meters": 350,
            "walk_time_minutes": 5,
            "steps": [
                f"Walk from {origin} towards main avenue",
                f"Head past central square to {destination}"
            ]
        }

    async def find_nearby_facilities(self, location_name: str, facility_type: str = "cafe") -> Dict[str, Any]:
        if self.api_key:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                        params={"location": "12.9716,77.5946", "radius": 1000, "type": facility_type, "key": self.api_key}
                    )
                    if resp.status_code == 200:
                        results = resp.json().get("results", [])[:3]
                        return {
                            "source": "live",
                            "near": location_name,
                            "facilities": [r.get("name") for r in results]
                        }
            except Exception as exc:
                print(f"[GoogleMapsAdapter] Live API call failed ({exc}). Falling back to mock response.")

        return {
            "source": "mock",
            "near": location_name,
            "facilities": ["Campus Coffee House", "Student Stationery Hub", "North Gate Pharmacy"]
        }
