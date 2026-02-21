import streamlit as st
import pandas as pd
import requests
import folium
import concurrent.futures
from geopy.distance import geodesic
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation


# ----------------------------------
# PAGE CONFIG
# ----------------------------------

st.set_page_config(layout="wide")
st.title("🚗 Ola Fleet Live Tracker")


# ----------------------------------
# GET USER GPS (SAFE METHOD)
# ----------------------------------

loc = get_geolocation()

if loc is None:

    st.warning("📍 Please allow location access and refresh.")
    st.stop()

USER_LAT = loc["coords"]["latitude"]
USER_LON = loc["coords"]["longitude"]

st.success(f"📍 Your Location: {USER_LAT:.6f}, {USER_LON:.6f}")


# ----------------------------------
# FILE UPLOAD
# ----------------------------------

file = st.file_uploader("📂 Upload Excel with VIN numbers", type="xlsx")

if file is None:

    st.info("Upload Excel file to start tracking.")
    st.stop()


df = pd.read_excel(file)

if "vehicleId" not in df.columns:

    st.error("Excel must contain 'vehicleId' column")
    st.stop()

VIN_LIST = df["vehicleId"].dropna().unique().tolist()


# ----------------------------------
# FETCH LIVE DATA FUNCTION
# ----------------------------------

def fetch_live(vin):

    try:

        url = f"https://y-ui.olacabs.com/track/{vin}"

        response = requests.get(url, timeout=10)

        if response.status_code != 200:

            return None

        data = response.json()

        lat, lon = map(float, data["location"].split(","))

        return {

            "VIN": vin,

            "Latitude": lat,
            "Longitude": lon,

            "Battery": data.get("batteryCharge"),

            "Last Updated": data.get("lastUpdated")

        }

    except:

        return None


# ----------------------------------
# PARALLEL FETCH
# ----------------------------------

st.info("Fetching live vehicle data...")

progress = st.progress(0)

results = []

total = len(VIN_LIST)


with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:

    future_to_vin = {

        executor.submit(fetch_live, vin): vin for vin in VIN_LIST

    }

    for i, future in enumerate(concurrent.futures.as_completed(future_to_vin)):

        result = future.result()

        if result:

            results.append(result)

        progress.progress((i + 1) / total)


if len(results) == 0:

    st.error("No live data received.")
    st.stop()


live_df = pd.DataFrame(results)


# ----------------------------------
# DISTANCE CALCULATION
# ----------------------------------

live_df["Distance (km)"] = live_df.apply(

    lambda row: geodesic(

        (USER_LAT, USER_LON),

        (row["Latitude"], row["Longitude"])

    ).km,

    axis=1

)


live_df = live_df.sort_values("Distance (km)")


TOP = live_df.head(30)


# ----------------------------------
# DISPLAY TABLE
# ----------------------------------

st.subheader("📋 Top 30 Nearest Vehicles")

st.dataframe(TOP, use_container_width=True)


# ----------------------------------
# MAP DISPLAY
# ----------------------------------

st.subheader("🗺 Vehicle Map")

m = folium.Map(location=[USER_LAT, USER_LON], zoom_start=13)


# user marker

folium.Marker(

    [USER_LAT, USER_LON],

    popup="You",

    icon=folium.Icon(color="blue")

).add_to(m)


# vehicle markers

for _, row in TOP.iterrows():

    folium.Marker(

        [row["Latitude"], row["Longitude"]],

        popup=f"""

<b>VIN:</b> {row['VIN']}<br>

<b>Battery:</b> {row['Battery']}<br>

<b>Last Updated:</b> {row['Last Updated']}<br>

<b>Distance:</b> {row['Distance (km)']:.2f} km<br>

<a href="https://www.google.com/maps?q={row['Latitude']},{row['Longitude']}" target="_blank">

Navigate

</a>

""",

        icon=folium.Icon(color="green")

    ).add_to(m)


st_folium(m, height=600, width=1200)


# ----------------------------------
# DONE
# ----------------------------------

st.success("✅ Live tracking complete")
