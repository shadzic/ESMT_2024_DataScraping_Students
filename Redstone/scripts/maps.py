import folium

# List of places with their names and coordinates (add coordinates for each place)
places = [
    {"name": "Dom Aussichtsplattform", "lat": 52.520008, "lon": 13.404954},
    {"name": "Havana Club", "lat": 52.522508, "lon": 13.412160},
    {"name": "Madami", "lat": 52.524370, "lon": 13.401580},
    {"name": "Mama Vân - Sài Gòn Deli", "lat": 52.519290, "lon": 13.406090},
    {"name": "Nero Pizza & Grill", "lat": 52.517040, "lon": 13.388880},
    {"name": "Neue Babylon Berlin GmbH", "lat": 52.530050, "lon": 13.385640},
    {"name": "SuperKato", "lat": 52.511520, "lon": 13.400170},
    {"name": "The Klub Kitchen", "lat": 52.526660, "lon": 13.401750},
    {"name": "Wackers Kaffee", "lat": 52.518260, "lon": 13.411520},
    {"name": "Weisses Bräuhaus", "lat": 52.521160, "lon": 13.405080},
]

# Center the map on a specific location (Berlin in this case)
map_center = [52.5200, 13.4050]
map_berlin = folium.Map(location=map_center, zoom_start=13)

# Add markers for each place
for place in places:
    folium.Marker(
        location=[place["lat"], place["lon"]],
        popup=place["name"],
        icon=folium.Icon(color="blue"),
    ).add_to(map_berlin)

# Save the map to an HTML file
map_berlin.save("places_map.html")

print("Map with places created and saved as 'places_map.html'.")
