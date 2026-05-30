# Infrared API — Incident Report
**Date:** 2026-05-30  
**API base URL:** `https://api.infrared.city/v2`  
**SDK version:** `infrared-sdk 0.4.9` (Python 3.12, Windows)  
**Affected site:** Astana / Bayterek–Nurzhol Blvd (51.128 °N, 71.430 °E)  
**Operation attempted:** Full baseline pipeline — buildings fetch → vegetation fetch → ground-material fetch → wind CFD → solar raycast → UTCI  

---

## Summary

Four distinct API endpoint groups are returning **HTTP 500 Internal Server Error**.  
Job submission (`run_area`) works and returns real job UUIDs, but the job-status  
polling endpoint (`check_area_state`) also returns 500, making it impossible to  
retrieve simulation results. The pipeline is completely blocked.

---

## Working endpoints

| Endpoint | Status |
|----------|--------|
| `GET /utils/gis/buildings` (via `buildings.get_area`) | ✅ Returns `AreaBuildings` object |
| `POST /area` / job submission (via `run_area`) | ✅ Jobs accepted — real UUIDs issued |

---

## Failing endpoints

### 1. `GET /utils/gis/vegetation` — HTTP 500

All tile requests return 500. SDK `vegetation.get_area()` returns an `AreaVegetation`
object with zero features (all tiles failed). Observed across ~35 tiles covering the
1 500 m context polygon.

**Example failing URL:**
```
GET https://api.infrared.city/v2/utils/gis/vegetation
    ?latitude=51.12241250449156
    &longitude=71.42109679751732
    &distance=363
    &source=fgb
→ 500 Internal Server Error
```

**Error pattern (repeated for every tile):**
```
requests.exceptions.HTTPError:
  500 Server Error: Internal Server Error for url:
  https://api.infrared.city/v2/utils/gis/vegetation?...
```

---

### 2. `GET /utils/ground-material/collect` — HTTP 500

All tile requests return 500 after 3 retry attempts each. Affects a 16-tile grid
covering the 500 m analysis polygon (Mapbox source).

**Example failing URL:**
```
GET https://api.infrared.city/v2/utils/ground-material/collect
    ?latitude=51.12465828242903
    &longitude=71.43200393625013
    &distance=363
    &source=mapbox
→ 500 Internal Server Error
```

**Error pattern:**
```
Tile 44e6e523-9a9b-5311-b1c6-545b64bd7dd0 failed after 3 attempts:
  500 Server Error: Internal Server Error for url:
  https://api.infrared.city/v2/utils/ground-material/collect?...
```

---

### 3. `GET /utils/weather/location` — HTTP 500

Weather station lookup returns 500 on every attempt (4 retries with exponential
back-off). No station UUID can be retrieved, blocking the UTCI simulation entirely.

**Endpoint called:**
```
GET https://api.infrared.city/v2/utils/weather/location
    ?lat=51.128&lon=71.430&radius=<configured_radius>
→ 500 Internal Server Error (after 4 attempts)
```

**SDK log:**
```
get_weather_file_from_location attempt 1/4 got HTTP 500, retrying in 0.8s
get_weather_file_from_location attempt 2/4 got HTTP 500, retrying in 2.5s
get_weather_file_from_location attempt 3/4 got HTTP 500, retrying in 5.1s
get_weather_file_from_location failed after 4 attempt(s): HTTP 500
```

---

### 4. `GET /area/{job_id}/state` — HTTP 500  ← **Primary blocker**

Simulation jobs are submitted successfully via `run_area` and receive valid UUIDs,
but subsequent status polling via `check_area_state` returns 500 on all attempts
(6 retries with exponential back-off per job). This makes it impossible to retrieve
any simulation result — wind, solar, or UTCI.

**16 jobs submitted, 0 results retrievable.**

**Submitted job UUIDs (all unresolvable):**
```
03d76815-522d-455d-b0bc-006756c36d9c
19ac38d8-3901-4488-a6bf-16baa1d7bbde
1d0b53be-874b-4b74-bfc8-5cecbac9306b
29c48c1e-78d8-49e1-8497-8bc11db0f7a0
3f9c2cd1-9122-4aab-9e28-40df25d9cda4
3fa40635-621f-4017-bd16-2f7e721fcb99
627b404b-67d8-43bb-91b1-2163a905225e
638c4e91-a6cc-43d7-b06d-b0d77a52b920
8d33aff4-8149-4c6b-84cc-4363241080c1
a24af90a-0668-4a87-86a0-a23d17888af3
a84d76af-23cc-4c3d-968b-e72e23c909ff
bda21c1a-9659-45cf-8efc-0ccdc2fa7b17
c33388ed-7e64-46e0-9a89-bc01e74b26ca
e39b4cb5-1e57-44f2-8a99-23e06b6abe85
edeaaaa9-eb7c-40e7-9e9b-caf04798e5f2
fb9d2be6-0b02-4ef7-a21b-dc9dc4e292d0
```

**Error pattern (repeated across all 16 jobs, 6 attempts each):**
```
check_area_state: job 03d76815-522d-455d-b0bc-006756c36d9c
  status query failed (attempt 1), retrying in 0.7s:
  Failed to poll job 03d76815-522d-455d-b0bc-006756c36d9c: 500
...
check_area_state: job 03d76815-522d-455d-b0bc-006756c36d9c
  status query failed after 6 attempts:
  Failed to poll job 03d76815-522d-455d-b0bc-006756c36d9c: 500
```

---

## Impact

| Simulation | Status |
|------------|--------|
| Wind CFD | ❌ Jobs submitted, results unreadable |
| Direct sun hours | ❌ Jobs submitted, results unreadable |
| UTCI thermal comfort | ❌ Blocked at weather station lookup |
| Scenario A/B/C/D | ❌ Cannot proceed without baseline |

The outage has been continuous for **at least 24 hours** (first observed 2026-05-29).
Previous runs attempted on the same API key at different coordinates (Riyadh, Mecca,
Almaty) produced valid results under the same code — confirming this is a server-side
regression, not a client-side issue.

---

## Reproduction

```python
import os
from infrared_sdk import InfraredClient

client = InfraredClient(api_key="<your_key>")

# Minimal reproduction — single tile vegetation fetch
polygon = {
    "type": "Polygon",
    "coordinates": [[
        [71.425, 51.123], [71.435, 51.123],
        [71.435, 51.133], [71.425, 51.133],
        [71.425, 51.123]
    ]]
}

# This returns AreaVegetation with 0 features (all tiles 500)
veg = client.vegetation.get_area(polygon)
print(veg.features)  # []

# Weather endpoint — always 500
stations = client.weather.get_weather_file_from_location(lat=51.128, lon=71.430)
# → raises after 4 retries

# check_area_state — always 500 even for freshly submitted jobs
schedule = client.run_area(wind_request, polygon, buildings=buildings)
# job IDs are returned but polling them fails immediately
```

---

## Environment

```
OS:          Windows 10, Python 3.12
SDK:         infrared-sdk 0.4.9
API base:    https://api.infrared.city/v2
Auth:        Bearer token (API key — available on request)
```
