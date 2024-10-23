from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import folium
import googlemaps
import time
from datetime import datetime, timedelta
import ticketpy
import requests
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

matplotlib.use('Agg')

app = Flask(__name__)

# Global variables to store retrieved data and API keys
df_sorted_tmaster = None
api_key_google = ""  # Replace with API Key
api_key_weather = ""  # Replace with API Key
gmaps = googlemaps.Client(key=api_key_google)

# TicketMaster API setup
tm_client = ticketpy.ApiClient('')

# OpenWeatherMap API setup
weather_url = "http://api.openweathermap.org/data/2.5/forecast"

# Function to retrieve route from OSRM
def get_osrm_route(airport_coords, venue_coords):
    """Calculate a route between two coordinates using OSRM."""
    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{airport_coords[1]},{airport_coords[0]};{venue_coords[1]},{venue_coords[0]}?overview=full&geometries=geojson"

    response = requests.get(osrm_url)
    if response.status_code == 200:
        data = response.json()
        if 'routes' in data and len(data['routes']) > 0:
            route_geometry = data['routes'][0]['geometry']  # GeoJSON route line
            return route_geometry
    return None

def get_ticketmaster_data(start_date, end_date):
    """Fetch event data from TicketMaster API."""
    pages = tm_client.events.find(
        country_code='DE',
        classification_name='music',
        start_date_time=f'{start_date}T12:00:00Z',
        end_date_time=f'{end_date}T12:00:00Z'
    ).all()
    
    event_data = []
    for event in pages:
        venue = event.venues[0]
        genre = None
        if event.classifications:
            classification = event.classifications[0]
            if hasattr(classification, 'genre') and classification.genre:
                genre = classification.genre.name
        event_dict = {
            'Event Name': event.name,
            'Event Date': event.utc_datetime,
            'Venue Name': venue.name,
            'Venue Address': venue.address,
            'Venue Postalcode': venue.postal_code,
            'Venue Latitude': venue.latitude,
            'Venue Longitude': venue.longitude,
            'Venue City': venue.city,
            'Box Office': venue.dmas,
            'Event Genre': genre
        }
        event_data.append(event_dict)

    df_all = pd.DataFrame(event_data)
    return df_all

def get_weather_forecast(lat, lon, event_date):
    """Fetch weather forecast from OpenWeatherMap API for a specific location and date."""
    # Call OpenWeatherMap API to get the forecast
    params = {
        'lat': lat,
        'lon': lon,
        'appid': api_key_weather,
        'units': 'metric'
    }
    
    response = requests.get(weather_url, params=params).json()

    # Check if the API returned the forecast list
    if 'list' not in response:
        return None

    # Iterate through forecast data to find the closest forecast to the event date/time
    for forecast in response['list']:
        forecast_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")

        # Find the closest forecast to the event date (within +/- 3 hours)
        if abs((forecast_time - event_date).total_seconds()) < 3 * 3600:
            weather_description = forecast['weather'][0]['description']
            temp = forecast['main']['temp']
            return f"{temp}°C, {weather_description}"
    
    return None
# Map on homepage for all events
def generate_map(df):
    """Generate a map using Folium to display event venues."""
    germany_map = folium.Map(location=[51.1657, 10.4515], zoom_start=6)
    
    for _, row in df.iterrows():
        venue_lat = row['Venue Latitude']
        venue_lon = row['Venue Longitude']
        event_name = row['Event Name']
        event_date = row['Event Date']
        event_temp = row['Weather Forecast']
        popup_content = f"{event_name} at {event_date}, Weather: {event_temp}."
        
        # Add markers for each event
        folium.Marker(
            location=[venue_lat, venue_lon],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=event_name
        ).add_to(germany_map)
    
    return germany_map
# Include bar chart visualization in website
def create_event_genre_city_chart(df):
    """Create a stacked bar chart showing event genres by city."""
    genre_city = df.groupby(['Venue City', 'Event Genre']).size().unstack(fill_value=0)
    
    # Plot and save the figure as an image
    fig, ax = plt.subplots(figsize=(12, 6))
    genre_city.plot(kind='bar', stacked=True, ax=ax, colormap='viridis')
    
    ax.set_title('Event Genres by City')
    ax.set_xlabel('City')
    ax.set_ylabel('Number of Events')
    plt.xticks(rotation=45)
    ax.legend(title='Event Genre')
    plt.tight_layout()
    
    # Save the plot as an image
    chart_path = 'static/event_genre_city_chart.png'
    plt.savefig(chart_path)
    plt.close()
    return chart_path

# Include bubble plot of weather vs. events
def create_bubble_plot(df):
    """Create a bubble plot showing the number of events by city with average temperature."""
    df['Temperature'] = df['Weather Forecast'].str.extract(r'(\d+\.\d+)').astype(float)
    
    # Count events per city and merge with temperature data
    events_count = df['Venue City'].value_counts().reset_index()
    events_count.columns = ['Venue City', 'Event Count']
    avg_temp = df.groupby('Venue City')['Temperature'].mean().reset_index()
    bubble_data = pd.merge(events_count, avg_temp, on='Venue City')

    # Create and save the plot
    fig, ax = plt.subplots(figsize=(12, 8))
    sns.scatterplot(
        data=bubble_data,
        x='Venue City', 
        y='Temperature', 
        size='Event Count', 
        sizes=(100, 1000), 
        ax=ax, 
        legend=False, 
        alpha=0.7
    )
    ax.set_title('Number of Events by City with Average Temperature')
    ax.set_xlabel('City')
    ax.set_ylabel('Temperature (°C)')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save the plot as an image
    bubble_chart_path = 'static/bubble_chart.png'
    plt.savefig(bubble_chart_path)
    plt.close()
    return bubble_chart_path


# Function to find the nearest commercial airport using Google Maps
def find_nearest_commercial_airport(lat, lon):
    places_result = gmaps.places_nearby(location=(lat, lon), radius=50000, type='airport', keyword='commercial')
    if places_result['results']:
        airport = places_result['results'][0]
        return airport['name'], airport['geometry']['location']['lat'], airport['geometry']['location']['lng']
    return None, None, None

# Function to calculate the distance and time between two locations using Google Maps
def calculate_distance_matrix(origins, destinations, mode='driving', departure_time=None):
    distance_matrix = gmaps.distance_matrix(origins, destinations, mode=mode, departure_time=departure_time)
    if distance_matrix['rows'][0]['elements'][0]['status'] == 'OK':
        distance_km = distance_matrix['rows'][0]['elements'][0]['distance']['value'] / 1000
        duration_minutes = distance_matrix['rows'][0]['elements'][0]['duration']['value'] / 60
        return distance_km, duration_minutes
    return None, None

# Function to find best reviewed restaurant or hotel
def find_best_reviewed_place(lat, lon, place_type):
    places_result = gmaps.places_nearby(location=(lat, lon), radius=2000, type=place_type, rank_by='prominence')
    best_place = None
    highest_rating = -1
    for place in places_result.get('results', []):
        rating = place.get('rating', 0)
        if rating > highest_rating:
            highest_rating = rating
            best_place = place
    if best_place:
        return best_place['name'], best_place['geometry']['location']['lat'], best_place['geometry']['location']['lng'], best_place['rating']
    return None, None, None, None

def generate_combined_route_map_osm(airport_coords, venues_info):
    """
    Generate a Folium map with multiple routes from the airport to each venue.
    
    :param airport_coords: Tuple containing (latitude, longitude) of the airport
    :param venues_info: List of dictionaries with each venue's coordinates and route geometry
    """
    # Initialize map centered around the airport
    combined_map = folium.Map(location=airport_coords, zoom_start=12)

    # Add airport marker
    folium.Marker(
        location=airport_coords, 
        popup="Nearest Airport", 
        icon=folium.Icon(color="blue")
    ).add_to(combined_map)

    # Add markers and routes for each venue
    for venue in venues_info:
        venue_coords = (venue['Venue Latitude'], venue['Venue Longitude'])
        route_geometry = venue['Route Geometry']

        # Add venue marker
        folium.Marker(
            location=venue_coords, 
            popup=venue['Venue Name'], 
            icon=folium.Icon(color="red")
        ).add_to(combined_map)

        # Add the route as a polyline if available
        if route_geometry:
            coordinates = route_geometry['coordinates']  # Extract GeoJSON coordinates
            route_coords = [(lat, lon) for lon, lat in coordinates]  # Convert to (lat, lon) format
            folium.PolyLine(route_coords, color="green", weight=5, opacity=0.8).add_to(combined_map)

    # Save the combined map as an HTML file
    map_path = 'combined_route_map_osm.html'
    combined_map.save(map_path)
    return map_path

# Function to process a single venue using Google Maps API and return the route
def process_single_venue(row):
    venue_lat = row['Venue Latitude']
    venue_lon = row['Venue Longitude']
    event_date = pd.to_datetime(row['Event Date'])
    event_date_minus_2_hours = event_date - timedelta(hours=2)
    departure_time = int(time.mktime(event_date_minus_2_hours.timetuple()))
    
    # Find nearest airport using Google Maps API
    airport_name, airport_lat, airport_lon = find_nearest_commercial_airport(venue_lat, venue_lon)
    if airport_name:
        airport_coords = (airport_lat, airport_lon)
        venue_coords = (venue_lat, venue_lon)
        airport_distance_km, airport_duration_minutes = calculate_distance_matrix(
            airport_coords, venue_coords, mode='driving', departure_time=departure_time
        )

        # Generate route using OSRM
        route_geometry = get_osrm_route(airport_coords, venue_coords)
    else:
        airport_distance_km, airport_duration_minutes, route_geometry = None, None, None

    # Get best-reviewed restaurant and hotel nearby
    restaurant_name, restaurant_lat, restaurant_lon, restaurant_rating = find_best_reviewed_place(venue_lat, venue_lon, 'restaurant')
    hotel_name, hotel_lat, hotel_lon, hotel_rating = find_best_reviewed_place(venue_lat, venue_lon, 'lodging')

    # Return the data, including airport latitude and longitude
    return {
        'Nearest Airport': airport_name,
        'Nearest Airport Latitude': airport_lat,
        'Nearest Airport Longitude': airport_lon,
        'Distance to Airport (km)': airport_distance_km,
        'Time to Airport (min)': airport_duration_minutes,
        'Best Restaurant': restaurant_name,
        'Restaurant Rating': restaurant_rating,
        'Best Hotel': hotel_name,
        'Hotel Rating': hotel_rating,
        'Route Geometry': route_geometry  # This will be None if no route is found
    }

# Route for the home page (TicketMaster data)
@app.route('/', methods=['GET', 'POST'])
def home():
    global df_sorted_tmaster
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        
        # Fetch TicketMaster data
        df_sorted_tmaster = get_ticketmaster_data(start_date, end_date)

        # Add weather forecast data for each event
        current_date = datetime.now()
        df_sorted_tmaster['Weather Forecast'] = None
        for index, row in df_sorted_tmaster.iterrows():
            event_date = pd.to_datetime(row['Event Date'])
            if 0 <= (event_date - current_date).days <= 5:
                lat = row['Venue Latitude']
                lon = row['Venue Longitude']
                forecast = get_weather_forecast(lat, lon, event_date)
                df_sorted_tmaster.at[index, 'Weather Forecast'] = forecast
            else:
                df_sorted_tmaster.at[index, 'Weather Forecast'] = "No forecast available"

        # Generate map for Germany events
        germany_map = generate_map(df_sorted_tmaster)
        germany_map.save('static/germany_events_map.html')

        genre_city_chart_path = create_event_genre_city_chart(df_sorted_tmaster)
        bubble_chart_path = create_bubble_plot(df_sorted_tmaster)

        return render_template(
            'home.html',
            df=df_sorted_tmaster.to_html(),
            map_file="germany_events_map.html",
            genre_chart=genre_city_chart_path,
            bubble_chart=bubble_chart_path
        )
    return render_template('home.html')

# Google Maps API page
@app.route('/googlemaps', methods=['GET', 'POST'])
def google_maps_page():
    global df_sorted_tmaster
    if df_sorted_tmaster is None:
        return redirect(url_for('home'))  # Redirect to home if no data available
    
    cities = df_sorted_tmaster['Venue City'].unique()

    if request.method == 'POST':
        selected_city = request.form['city']
        
        # Filter dataframe by selected city and create a copy
        df_city = df_sorted_tmaster[df_sorted_tmaster['Venue City'] == selected_city].copy()

        # Initialize new columns in the dataframe
        df_city['Nearest Airport'] = None
        df_city['Distance to Airport (km)'] = None
        df_city['Time to Airport (min)'] = None
        df_city['Best Restaurant'] = None
        df_city['Restaurant Rating'] = None
        df_city['Best Hotel'] = None
        df_city['Hotel Rating'] = None
        df_city['Route Geometry'] = None

        # Process each venue in the selected city and collect their information
        venues_info = []
        airport_coords = None

        for index, row in df_city.iterrows():
            # Get processed venue data
            venue_info = process_single_venue(row)
            
            # Add the processed data to the dataframe
            df_city.at[index, 'Nearest Airport'] = venue_info['Nearest Airport']
            df_city.at[index, 'Distance to Airport (km)'] = venue_info['Distance to Airport (km)']
            df_city.at[index, 'Time to Airport (min)'] = venue_info['Time to Airport (min)']
            df_city.at[index, 'Best Restaurant'] = venue_info['Best Restaurant']
            df_city.at[index, 'Restaurant Rating'] = venue_info['Restaurant Rating']
            df_city.at[index, 'Best Hotel'] = venue_info['Best Hotel']
            df_city.at[index, 'Hotel Rating'] = venue_info['Hotel Rating']
            df_city.at[index, 'Route Geometry'] = venue_info['Route Geometry']

            # Collect venue information for combined map generation
            if venue_info['Route Geometry']:  # Check if the route was found
                venues_info.append({
                    'Venue Name': row['Venue Name'],
                    'Venue Latitude': row['Venue Latitude'],
                    'Venue Longitude': row['Venue Longitude'],
                    'Route Geometry': venue_info['Route Geometry']
                })
            
            # Set airport coordinates (assuming the same airport for all venues in the city)
            if not airport_coords and venue_info['Nearest Airport']:
                airport_coords = (venue_info['Nearest Airport Latitude'], venue_info['Nearest Airport Longitude'])

        # Check if any venues and airport data exist
        if venues_info and airport_coords:
            combined_map_path = generate_combined_route_map_osm(airport_coords, venues_info)
            map_file = combined_map_path  # Ensure this is passed to the template
        else:
            map_file = None

        # Render the updated dataframe to the HTML page
        venue_list = df_city.to_dict(orient='records')
        return render_template('googlemaps.html', cities=cities, venues=venue_list, map_file=combined_map_path)

    return render_template('googlemaps.html', cities=cities)

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)