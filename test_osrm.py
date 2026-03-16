import requests
import polyline

OSRM_URL = "http://localhost:5000"
# Alcalá de Henares to Ciudad Real coords (approx)
start = (40.4819, -3.3635)
end = (38.9848, -3.9273)

path = f"/route/v1/driving/{start[1]},{start[0]};{end[1]},{end[0]}?overview=full"
url = f"{OSRM_URL}{path}"

print(f"Testing URL: {url}")
try:
    response = requests.get(url, timeout=5)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if "routes" in data and len(data["routes"]) > 0:
            geom = data["routes"][0].get("geometry")
            print(f"Geometry type: {type(geom)}")
            print(f"Geometry snippet: {geom[:50]}...")
            try:
                decoded = polyline.decode(geom)
                print(f"Successfully decoded. Number of points: {len(decoded)}")
            except Exception as e:
                print(f"Failed to decode: {e}")
        else:
            print("No routes found in response.")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
