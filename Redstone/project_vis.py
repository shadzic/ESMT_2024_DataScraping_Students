import os

import folium
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from streamlit_folium import folium_static

# Load the final dataset
df = pd.read_csv(
    "/Users/matiascam/Documents/Data_Scraping/Redstone/data/final_vehicle_places_weather_data.csv"
)

# Load environment variables from .env file
load_dotenv(dotenv_path="./data/.env")

# load Google API
google_api_key = os.getenv("GOOGLE_API_KEY")


# Function to create a map with vehicle locations and tourist places
def create_map(df, origin_coords=None, destination_coords=None):
    # Center the map on Berlin
    map_center = [52.5200, 13.4050]
    map_berlin = folium.Map(location=map_center, zoom_start=12)

    # Plot available vehicles on the map
    for idx, row in df.iterrows():
        color = "blue" if row["vehicle_type"] == "bike" else "red"
        folium.Marker(
            [row["latitude"], row["longitude"]],
            popup=(
                f"Vehicle: {row['vehicle_type']}, Nearest place:"
                f" {row['nearest_place_name']}, Distance to place:"
                f" {row['distance_to_place']}m"
            ),
            icon=folium.Icon(color=color),
        ).add_to(map_berlin)

    # Add the origin and destination points if provided
    if origin_coords:
        folium.Marker(
            (origin_coords.latitude, origin_coords.longitude),
            popup="Origin",
            icon=folium.Icon(color="green"),
        ).add_to(map_berlin)
    if destination_coords:
        folium.Marker(
            (destination_coords.latitude, destination_coords.longitude),
            popup="Destination",
            icon=folium.Icon(color="purple"),
        ).add_to(map_berlin)

    return map_berlin


# Function to get the route from Google Maps Directions API
def get_route_from_google(origin_coords, destination_coords, google_api_key):
    directions_url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin_coords.latitude},{origin_coords.longitude}",
        "destination": (
            f"{destination_coords.latitude},{destination_coords.longitude}"
        ),
        "mode": "bicycling",
        "key": google_api_key,
    }
    response = requests.get(directions_url, params=params)
    route_data = response.json()
    if route_data["status"] == "OK":
        route = route_data["routes"][0]["legs"][0]
        return route
    else:
        st.error("Error fetching directions from Google API.")
        return None


# Add the route to the folium map
def add_route_to_map(map_berlin, route):
    steps = route["steps"]
    for step in steps:
        start_lat = step["start_location"]["lat"]
        start_lng = step["start_location"]["lng"]
        end_lat = step["end_location"]["lat"]
        end_lng = step["end_location"]["lng"]
        folium.PolyLine(
            [(start_lat, start_lng), (end_lat, end_lng)],
            color="blue",
            weight=2.5,
            opacity=1,
        ).add_to(map_berlin)


# Streamlit App UI
st.title("Bike/Scooter Rental Route Planner with Weather and Tourist Spots")

# Input Section
st.header("Select your route and vehicle type")
origin_input = st.text_input(
    "Enter your starting location (e.g., Brandenburg Gate)"
)
destination_input = st.text_input(
    "Enter your destination (e.g., Alexanderplatz)"
)
vehicle_type_input = st.selectbox("Choose your vehicle", ["bike", "scooter"])

# Display Weather Information
st.subheader("Weather Conditions Today")
st.write(f"Average Temperature: {df['tavg'].iloc[0]} °C")
st.write(f"Precipitation: {df['prcp'].iloc[0]} mm")
st.write(f"Wind Speed: {df['wspd'].iloc[0]} km/h")
st.write(f"Sunshine Duration: {df['tsun'].iloc[0]} minutes")

# Geocoding: Convert user inputs (addresses) to coordinates
geolocator = Nominatim(user_agent="geoapiExercises")
origin_coords = geolocator.geocode(origin_input) if origin_input else None
destination_coords = (
    geolocator.geocode(destination_input) if destination_input else None
)

# Create and display the map with available vehicles and tourist places
if origin_coords and destination_coords:
    st.subheader("Your Route Map")

    # Get route using Google API
    route = get_route_from_google(
        origin_coords, destination_coords, google_api_key
    )

    # Create the map and add the route
    map_berlin = create_map(
        df,
        origin_coords=(origin_coords.latitude, origin_coords.longitude),
        destination_coords=(
            destination_coords.latitude,
            destination_coords.longitude,
        ),
    )

    if route:
        add_route_to_map(map_berlin, route)

    folium_static(map_berlin)
else:
    st.warning("Please enter valid origin and destination locations.")

# If no locations are provided, still show the map with vehicles and places
if not origin_input or not destination_input:
    st.subheader("Available Vehicles and Tourist Places")
    map_berlin = create_map(df)
    folium_static(map_berlin)
