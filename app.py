from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import folium
import googlemaps
import time
from datetime import datetime, timedelta
import ticketpy
import requests

app = Flask(__name__)

# Global variables to store retrieved data and API keys
df_sorted_tmaster = None
api_key_google = ""  # Replace with your actual Google API key
api_key_weather = ""  # Replace with your actual OpenWeatherMap API key
gmaps = googlemaps.Client(key=api_key_google)

# TicketMaster API setup
tm_client = ticketpy.ApiClient('')

# OpenWeatherMap API setup
weather_url = "http://api.openweathermap.org/data/2.5/forecast"

# Function to get TicketMaster data
def get_ticketmaster_data(start_date, end_date):
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

# Function to fetch the weather forecast from OpenWeatherMap
def get_weather_forecast(lat, lon, event_date):
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

# Function to generate the Germany map with events and weather forecast
def generate_map(df):
    germany_map = folium.Map(location=[51.1657, 10.4515], zoom_start=6)
    for _, row in df.iterrows():
        venue_lat = row['Venue Latitude']
        venue_lon = row['Venue Longitude']
        event_name = row['Event Name']
        event_date = row['Event Date']
        event_temp = row['Weather Forecast']
        popup_content = f"{event_name} at {event_date}, Weather: {event_temp}."
        folium.Marker(
            location=[venue_lat, venue_lon],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=event_name
        ).add_to(germany_map)
    return germany_map

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

        return render_template('home.html', df=df_sorted_tmaster.to_html(), map_file="germany_events_map.html")
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

        # Process each venue in the selected city
        for index, row in df_city.iterrows():
            # Get processed Google Maps data for this venue
            venue_info = process_single_venue(row)
            
            # Add the Google Maps data to the dataframe
            df_city.at[index, 'Nearest Airport'] = venue_info['Nearest Airport']
            df_city.at[index, 'Distance to Airport (km)'] = venue_info['Distance to Airport (km)']
            df_city.at[index, 'Time to Airport (min)'] = venue_info['Time to Airport (min)']
            df_city.at[index, 'Best Restaurant'] = venue_info['Best Restaurant']
            df_city.at[index, 'Restaurant Rating'] = venue_info['Restaurant Rating']
            df_city.at[index, 'Best Hotel'] = venue_info['Best Hotel']
            df_city.at[index, 'Hotel Rating'] = venue_info['Hotel Rating']

        # Render the updated dataframe to the HTML page
        return render_template('googlemaps.html', cities=cities, venue_df=df_city.to_html())

    return render_template('googlemaps.html', cities=cities)
# Incorporate Visualization about average time to airport

# Function to process a single venue using Google Maps API
def process_single_venue(row):
    venue_lat = row['Venue Latitude']
    venue_lon = row['Venue Longitude']
    event_date = pd.to_datetime(row['Event Date'])
    event_date_minus_2_hours = event_date - timedelta(hours=2)
    departure_time = int(time.mktime(event_date_minus_2_hours.timetuple()))
    
    airport_name, airport_lat, airport_lon = find_nearest_commercial_airport(venue_lat, venue_lon)
    if airport_name:
        venue_coords = (venue_lat, venue_lon)
        airport_coords = (airport_lat, airport_lon)
        airport_distance_km, airport_duration_minutes = calculate_distance_matrix(
            venue_coords, airport_coords, mode='driving', departure_time=departure_time
        )
    else:
        airport_distance_km, airport_duration_minutes = None, None

    restaurant_name, restaurant_lat, restaurant_lon, restaurant_rating = find_best_reviewed_place(venue_lat, venue_lon, 'restaurant')
    hotel_name, hotel_lat, hotel_lon, hotel_rating = find_best_reviewed_place(venue_lat, venue_lon, 'lodging')

    return {
        'Nearest Airport': airport_name,
        'Distance to Airport (km)': airport_distance_km,
        'Time to Airport (min)': airport_duration_minutes,
        'Best Restaurant': restaurant_name,
        'Restaurant Rating': restaurant_rating,
        'Best Hotel': hotel_name,
        'Hotel Rating': hotel_rating
    }

# Function to find the nearest commercial airport
def find_nearest_commercial_airport(lat, lon):
    places_result = gmaps.places_nearby(location=(lat, lon), radius=50000, type='airport', keyword='commercial')
    if places_result['results']:
        airport = places_result['results'][0]
        return airport['name'], airport['geometry']['location']['lat'], airport['geometry']['location']['lng']
    return None, None, None

# Function to calculate the distance to the nearest airport
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

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)