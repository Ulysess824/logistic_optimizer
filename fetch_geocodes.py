import urllib.request
import json
import urllib.parse
places = [
    'Vícar, Almería, Spain',
    'Canovelles, Barcelona, Spain',
    'S.Paio de Oleiros, Portugal',
    'Porriño, Pontevedra, Spain'
]

for p in places:
    url = 'https://nominatim.openstreetmap.org/search?q=' + urllib.parse.quote(p) + '&format=json&limit=1'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data:
                print(f"{p} -> {data[0]['lat']}, {data[0]['lon']}")
            else:
                print(f"{p} -> Not found")
    except Exception as e:
        print(e)
