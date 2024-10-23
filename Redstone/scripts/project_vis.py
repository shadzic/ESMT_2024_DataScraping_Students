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
def create_map(
    df,
    origin_coords=None,
    destination_coords=None,
    selected_place_coords=None,
    selected_place_info=None,
    filter_vehicles=True,
):
    map_center = [52.5200, 13.4050]  # Center the map on Berlin
    map_berlin = folium.Map(location=map_center, zoom_start=12)

    # Plot available vehicles on the map, optionally filter unused vehicles
    for idx, row in df.iterrows():
        color = "blue" if row["vehicle_type"] == "bike" else "red"

        # Optional: Filter out vehicles that are far from the origin or route
        if filter_vehicles:
            vehicle_coords = (row["latitude"], row["longitude"])
            if (
                origin_coords
                and geodesic(origin_coords, vehicle_coords).meters > 1000
            ):
                continue  # Skip vehicles that are farther than 1 km from origin or route

        # Add the vehicles to the map with smaller markers
        folium.CircleMarker(
            [row["latitude"], row["longitude"]],
            radius=3,  # Make the markers smaller
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=(
                f"Vehicle: {row['vehicle_type']}, Nearest place:"
                f" {row['nearest_place_name']}, Distance to place:"
                f" {row['distance_to_place']}m"
            ),
        ).add_to(map_berlin)

    # Add the origin and destination points
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

    # Add the selected place marker if a place is selected
    if selected_place_coords and selected_place_info:
        folium.Marker(
            selected_place_coords,
            popup=(
                "Selected Place:"
                f" {selected_place_info['name']} ({selected_place_info['category']})"
            ),
            icon=folium.Icon(color="orange"),
        ).add_to(map_berlin)

    return map_berlin


# Function to get the route and travel time from Google Maps Directions API
def get_route_and_time(origin_coords, destination_coords, mode, google_api_key):
    directions_url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin_coords[0]},{origin_coords[1]}",
        "destination": f"{destination_coords[0]},{destination_coords[1]}",
        "mode": mode,  # Can be "walking", "bicycling", or "driving"
        "key": google_api_key,
    }
    response = requests.get(directions_url, params=params)
    route_data = response.json()
    if route_data["status"] == "OK":
        route = route_data["routes"][0]["legs"][0]
        duration_text = route["duration"][
            "text"
        ]  # Travel time in text format (e.g., '15 mins')
        duration_value = (
            route["duration"]["value"] / 60
        )  # Travel time in minutes (Google provides it in seconds)
        return route, duration_text, duration_value
    else:
        st.error("Error fetching directions from Google API.")
        return None, None, None


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


# Function to find places near the route (within a certain distance, e.g., 500m)
def get_places_near_route(route, df, max_distance=500):
    nearby_places = []
    for step in route["steps"]:
        step_coords = (
            step["start_location"]["lat"],
            step["start_location"]["lng"],
        )
        for idx, row in df.iterrows():
            place_coords = (row["latitude"], row["longitude"])
            distance = geodesic(step_coords, place_coords).meters
            if distance <= max_distance:
                nearby_places.append(
                    {
                        "name": row["nearest_place_name"],
                        "category": row["place_category"],
                        "latitude": row["latitude"],
                        "longitude": row["longitude"],
                    }
                )
    return nearby_places


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
st.title("Bike/Scooter Rental Route Planner with Place Category Selection")

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

    # Set the mode based on the vehicle type
    mode = "bicycling" if vehicle_type_input == "bike" else "driving"

    # Get the initial route and travel time
    initial_route, travel_time_text, travel_time_minutes = get_route_and_time(
        origin_coords, destination_coords, mode, google_api_key
    )

    # Find places that are near the route (within 500 meters)
    places_near_route = get_places_near_route(
        initial_route, df, max_distance=500
    )

    # Allow the user to filter places by category
    st.subheader("Filter places by category")
    available_categories = list(
        set([place["category"] for place in places_near_route])
    )
    selected_category = st.selectbox(
        "Choose a category", ["All"] + available_categories
    )

    # Filter the places based on the selected category
    if selected_category != "All":
        places_near_route = [
            place
            for place in places_near_route
            if place["category"] == selected_category
        ]

    # Allow the user to select a place to visit along the way
    st.subheader("Select a place to visit along the way (optional)")
    selected_place = st.selectbox(
        "Choose a place",
        ["None"] + [place["name"] for place in places_near_route],
    )

    selected_place_coords = None  # Initialize as None for non-selected place
    selected_place_info = None  # Initialize as None for non-selected place

    if selected_place != "None":
        # Get the coordinates and category of the selected place
        selected_place_info = next(
            place
            for place in places_near_route
            if place["name"] == selected_place
        )
        selected_place_coords = (
            selected_place_info["latitude"],
            selected_place_info["longitude"],
        )

        # Get the route from origin to selected place, and then from selected place to destination
        route_to_place, _, time_to_place = get_route_and_time(
            origin_coords, selected_place_coords, mode, google_api_key
        )
        route_to_destination, _, time_to_destination = get_route_and_time(
            selected_place_coords, destination_coords, mode, google_api_key
        )

        # Update the total travel time
        total_travel_time = time_to_place + time_to_destination
        travel_time_text = f"{total_travel_time:.1f} minutes"

        # Calculate the final price
        price = 0.5 * total_travel_time + 1  # 0.5 per minute + 1 for unlocking

        # Create the map and add the updated route (origin -> place -> destination)
        map_berlin = create_map(
            df,
            origin_coords=origin_coords,
            destination_coords=destination_coords,
            selected_place_coords=selected_place_coords,
            selected_place_info=selected_place_info,
        )
        add_route_to_map(
            map_berlin, route_to_place
        )  # Add the route from origin to selected place
        add_route_to_map(
            map_berlin, route_to_destination
        )  # Add the route from selected place to destination

    else:
        # No place selected, proceed with the direct route
        total_travel_time = travel_time_minutes
        price = 0.5 * total_travel_time + 1

        # Create the map and add the direct route (origin -> destination)
        map_berlin = create_map(
            df,
            origin_coords=origin_coords,
            destination_coords=destination_coords,
        )
        add_route_to_map(map_berlin, initial_route)

    st_folium(map_berlin, width=700, height=500)

    # Display travel time and price
    st.subheader("Estimated Travel Time and Price:")
    st.write(f"Travel Time: {travel_time_text}")
    st.write(f"Price: ${price:.2f}")

else:
    st.warning("Please enter valid origin and destination locations.")

# If no locations are provided, still show the map with vehicles and places
if not origin_input or not destination_input:
    st.subheader("Available Vehicles and Tourist Places")
    map_berlin = create_map(df)
    st_folium(map_berlin, width=700, height=500)
