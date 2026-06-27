import numpy as np
import pandas as pd
from astropy.time import Time
from astropy.coordinates import EarthLocation, SkyCoord
import astropy.units as u
from astroplan import Observer, FixedTarget
from astroquery.simbad import Simbad
#from geopy.geocoders import Nominatim

import warnings
from astroplan import TargetAlwaysUpWarning

# Suppress just this specific warning
warnings.filterwarnings('ignore', category=TargetAlwaysUpWarning)

def azimuth_to_cardinal(azimuth, points=8):
    """
    Converts azimuth degrees (0-360) into standard cardinal points.
    Accepts points=4 (N, E, S, W) or points=8 (N, NE, E, SE, S, SW, W, NW).
    """
    # Ensure azimuth stays within 0 to 360 degrees
    azimuth = azimuth % 360
    
    if points == 4:
        directions = ["N", "E", "S", "W"]
    elif points == 8:
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    else:
        raise ValueError("Points parameter must be 4 or 8.")
        
    # Calculate index by dividing 360 degrees into equal wedges
    num_directions = len(directions)
    wedge_size = 360 / num_directions
    
    # Add half a wedge size to center the degree range on the cardinal point
    idx = int((azimuth + (wedge_size / 2)) / wedge_size) % num_directions
    
    return directions[idx]

# --- Quick Test ---
#test_degrees = [0, 45, 90, 185, 270, 355]

#print("8-Point Conversion:")
#for deg in test_degrees:
#    print(f"{deg}° -> {azimuth_to_cardinal(deg, points=8)}")

# Initialize the geocoder (provide a unique app name for the user_agent)
geolocator = Nominatim(user_agent="my_location_app")

# Define the address you want to find
address = "Wiesenstrasse 58 64331 Weiterstadt Germany"
location = geolocator.geocode(address)

# Check if a location was found and print the coordinates
if location:
    print(f"Address: {location.address}")
    print(f"Latitude: {location.latitude}, Longitude: {location.longitude}")
    print(location)
else:
    print("Address not found.")

# 1. Define Observation Location (Example: Reichelsheim, Germany)
# Replace with your exact latitude, longitude, and elevation
location = EarthLocation(lat=location.latitude*u.deg, lon=location.longitude*u.deg, height=110*u.m)
observer = Observer(location=location, name="Home Observatory")

# 2. Define Observation Time
# Input the specific year, month, day, and UTC time
obs_time = Time("2026-06-20 22:00:00") # Format: YYYY-MM-DD HH:MM:SS (UTC)

# 3. Define Deep Sky Object Targets
# You can add coordinates manually or fetch them automatically by name
target_list = [
    {"name": "NGC6960/C34 (Western Veil)",     "id": "NGC6960"},
    {"name": "NGC6992/C33 (Eastern Veil)",     "id": "NGC6992"},
    {"name": "NGC7635     (Bubble nebula)",    "id": "NGC7635"},
    {"name": "M31         (Andromeda Galaxy)", "id": "M31"},
    {"name": "M42         (Orion Nebula)",     "id": "M42"},
    {"name": "M51         (Whirlpool Galaxy)", "id": "M51"},
    {"name": "M13         (Hercules Cluster)", "id": "M13"}
]

# 4. Calculate Coordinates and Build Database
db_records = []

for item in target_list:
    try:
        # Fetch target coordinates from online catalogs (SIMBAD/NED)
        target = FixedTarget.from_name(item["id"], name=item["name"])
        # Calculate horizontal coordinates (Alt/Az) for the observer at that time
        altaz = observer.altaz(obs_time, target)
        
        # Extract components
        altitude = altaz.alt.degree
        azimuth = altaz.az.degree
        zenith = 90.0 - altitude # Zenith angle is the complement of altitude
        
        # Get Rise and Fall (Set) Times
        rise_time = observer.target_rise_time(obs_time, target, which="next")
        set_time = observer.target_set_time(obs_time, target, which="next")
        #print(f"Next Rise Time (UTC): {rise_time.iso}")
        #print(f"Next Set Time (UTC): {set_time.iso}")
        # Check if it's always up before trying to find rise/set times
        if observer.target_is_always_up(obs_time, target):
             print(f"{item["name"]} is circumpolar and always above the horizon!")
        #Simbad.add_votable_fields('dim')  
        #result_table = Simbad.query_object(target)
        
        # Extract major and minor dimensions
        #maj_axis = result_table['GALDIM_MAJAXIS'][0]
        #min_axis = result_table['GALDIM_MINAXIS'][0]
        #unit = result_table['GALDIM_MAJAXIS'].unit
                
        # Append data row
        db_records.append({
            "Target Name": target.name,
            "RA (deg)": target.coord.ra.degree,
            "Dec (deg)": target.coord.dec.degree,
            "Azimuth (deg)": round(azimuth, 2),
            "Cardinal ": azimuth_to_cardinal(azimuth, points=8),
            "Altitude (deg)": round(altitude, 2),
            "Zenith (deg)": round(zenith, 2),
            "Rise Time": rise_time.iso,
            "Set  Time": set_time.iso,           
            "Visible Now": altitude > 0 # True if above the horizon
        })
    except Exception as e:
        print(f"Could not fetch data for {item['name']}: {e}")

# 5. Convert to Pandas DataFrame
df = pd.DataFrame(db_records)

# Display the resulting database table
print(f"\n--- DSO Database for {obs_time} UTC ---")
print(df.to_string(index=False))

# 6. Optional: Save database to a CSV file
# df.to_csv("dso_database.csv", index=False)



