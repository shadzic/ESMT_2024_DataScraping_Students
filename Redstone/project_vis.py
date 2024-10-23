import os

import folium
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from geopy.distance import geodesic
from streamlit_folium import st_folium

# Load the final dataset
df = pd.read_csv(
    "/Users/matiascam/Documents/Data_Scraping/Redstone/data/final_vehicle_places_weather_data.csv"
)

# Load environment variables from .env file
load_dotenv(
    dotenv_path="/Users/matiascam/Documents/Data_Scraping/Redstone/data/.env"
)

# Load Google API key from environment variables
google_api_key = os.getenv("GOOGLE_API_KEY")


# Function to create a map with vehicle locations and tourist places
def create_map(df, origin_coords=None, destination_coords=None):
    map_center = [52.5200, 13.4050]  # Center the map on Berlin
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
            origin_coords, popup="Origin", icon=folium.Icon(color="green")
        ).add_to(map_berlin)
    if destination_coords:
        folium.Marker(
            destination_coords,
            popup="Destination",
            icon=folium.Icon(color="purple"),
        ).add_to(map_berlin)

    return map_berlin


# Function to get the route from Google Maps Directions API
def get_route_from_google(origin_coords, destination_coords, google_api_key):
    directions_url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin_coords[0]},{origin_coords[1]}",
        "destination": f"{destination_coords[0]},{destination_coords[1]}",
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


# Function to get coordinates using Google Geocoding API
def get_coordinates_from_google(address, google_api_key):
    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={google_api_key}"
    response = requests.get(geocode_url)
    geocode_data = response.json()
    if geocode_data["status"] == "OK":
        location = geocode_data["results"][0]["geometry"]["location"]
        return (location["lat"], location["lng"])
    else:
        st.error(
            "Error fetching coordinates from Google API:"
            f" {geocode_data['status']}"
        )
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


# Add tourist places along the route
def add_places_along_route(map_berlin, route, df):
    for idx, row in df.iterrows():
        for step in route["steps"]:
            start_coords = (
                step["start_location"]["lat"],
                step["start_location"]["lng"],
            )
            place_coords = (row["latitude"], row["longitude"])
            distance = geodesic(start_coords, place_coords).meters
            if distance < 500:  # 500 meters from route
                folium.Marker(
                    place_coords,
                    popup=(
                        "Place:"
                        f" {row['nearest_place_name']} ({row['place_category']})"
                    ),
                    icon=folium.Icon(color="green"),
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

# Get coordinates using Google Geocoding API
origin_coords = (
    get_coordinates_from_google(origin_input, google_api_key)
    if origin_input
    else None
)
destination_coords = (
    get_coordinates_from_google(destination_input, google_api_key)
    if destination_input
    else None
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
        df, origin_coords=origin_coords, destination_coords=destination_coords
    )

    if route:
        add_route_to_map(map_berlin, route)
        add_places_along_route(map_berlin, route, df)

    st_folium(map_berlin, width=700, height=500)
else:
    st.warning("Please enter valid origin and destination locations.")

# If no locations are provided, still show the map with vehicles and places
if not origin_input or not destination_input:
    st.subheader("Available Vehicles and Tourist Places")
    map_berlin = create_map(df)
    st_folium(map_berlin, width=700, height=500)
