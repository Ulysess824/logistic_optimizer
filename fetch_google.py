import logging
import googlemaps
from src.config import GOOGLE_MAPS_API_KEY
from src.utils.geo import GeoUtils

gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

places = [
    'Smurfit Westrock Almeria, Lugar Finca el Vizconde, Carretera Iryda Sector IV, La Canal - Paraje El Vizconde, 04738 Vícar, Almería',
    'Smurfit Westrock Canovelles, Polígono Industrial Can Castells 112-114, 08420 Canovelles, Barcelona',
    'Smurfit Westrock Celpack, Rua Da Concharinha 256, 4536-907 S.Paio de Oleiros, Portugal',
    'Smurfit Westrock Vigo, Ctra. Coruña-Portugal km 160, 36400 Porriño Pontevedra'
]

for p in places:
    res = gmaps.geocode(p)
    if res:
        lat = res[0]['geometry']['location']['lat']
        lng = res[0]['geometry']['location']['lng']
        print(f"{p} -> LAT: {lat}, LNG: {lng}")
    else:
        print(f"{p} -> Not found")
