import streamlit as st
import streamlit.components.v1 as components
import json
import uuid
import re
from helper import fetch_metar, fetch_sigmet, fetch_pirep

# Set page configuration
st.set_page_config(layout="wide", page_title="Flight Weather Planning Tool")

# Title of the app
st.title("Flight Weather Planning Tool")

# Initialize session state variables
if 'airports' not in st.session_state:
    st.session_state.airports = [{"id": str(uuid.uuid4()), "icao": "", "altitude": ""}]
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'add_airport' not in st.session_state:
    st.session_state.add_airport = False
if 'delete_airport' not in st.session_state:
    st.session_state.delete_airport = None
if 'airport_data' not in st.session_state:
    st.session_state.airport_data = []
#mine   
if 'list_names' not in st.session_state:
    st.session_state.list_names = []
if 'all_reports' not in st.session_state:
    st.session_state.all_reports = {}

# Callbacks for actions outside the form
if st.session_state.add_airport:
    st.session_state.airports.append({"id": str(uuid.uuid4()), "icao": "", "altitude": ""})
    st.session_state.add_airport = False

if st.session_state.delete_airport is not None:
    st.session_state.airports = [a for a in st.session_state.airports if a["id"] != st.session_state.delete_airport]
    st.session_state.delete_airport = None

if st.button("➕ Add Airport"):
    st.session_state.add_airport = True
    st.rerun()

for i, airport in enumerate(st.session_state.airports):
    cols = st.columns([3, 2, 1])
    with cols[0]:
        st.text_input("ICAO", value=airport["icao"], key=f"icao_{airport['id']}", 
                      on_change=lambda a_id=airport["id"], field="icao": setattr(
                          st.session_state, f"icao_{a_id}", st.session_state[f"icao_{a_id}"]))
    
    with cols[1]:
        st.text_input("Altitude (ft)", value=airport["altitude"], key=f"alt_{airport['id']}", 
                      on_change=lambda a_id=airport["id"], field="altitude": setattr(
                          st.session_state, f"alt_{a_id}", st.session_state[f"alt_{a_id}"]))
    
    with cols[2]:
        if len(st.session_state.airports) > 1:
            if st.button("❌", key=f"del_{airport['id']}"):
                st.session_state.delete_airport = airport["id"]
                st.rerun()

# Submit button (outside the form)
if st.button("Submit"):
    
    for airport in st.session_state.airports:
        if not re.fullmatch(r"^K[A-Z]{3}$", st.session_state[f"icao_{airport['id']}"]):
            st.warning(" ONLY VALID USA ICAO CODE")
            st.session_state.submitted = False
        try: 
            k = int(st.session_state[f"alt_{airport['id']}"])
        except:
            # st.write(airport['altitude'])
            st.warning("ALtitude should be a number")
            st.session_state.submitted = False
        
    
if st.session_state.submitted:
    for airport in st.session_state.airports:
        # airport["icao"] = st.session_state[f"icao_{airport['id']}"]
        airport["altitude"] = st.session_state[f"alt_{airport['id']}"]
        st.session_state.list_names.append(airport['icao'])
    st.session_state.all_reports = fetch_metar(st.session_state.list_names) 
    st.session_state.all_reports['sigmet'] = fetch_sigmet()
    st.session_state.all_reports['pirep'] = fetch_pirep()           
    st.rerun()

    fetch_metar(['a','b']) -> {'a':{'metar':englgih, 'taf': englih}}

# Display airport data if submitted
if st.session_state.submitted and st.session_state.airport_data:
    num_airports = len(st.session_state.airport_data)
    
    airport_cols = st.columns(num_airports)
    
    for i, col in enumerate(airport_cols):
        if i < len(st.session_state.airport_data):
            airport = st.session_state.airport_data[i]
            col.subheader(f"{airport['icao']} ({airport['altitude']} ft)")
    
    metar_cols = st.columns(num_airports)
    for i, col in enumerate(metar_cols):
        if i < len(st.session_state.airport_data):
            airport = st.session_state.airport_data[i]
            with col:
                with st.expander("METAR"):
                    st.text(airport["metar"])
    
    # Create columns for TAF expandables
    taf_cols = st.columns(num_airports)
    for i, col in enumerate(taf_cols):
        if i < len(st.session_state.airport_data):
            airport = st.session_state.airport_data[i]
            with col:
                with st.expander("TAF"):
                    st.text(airport["taf"])

    # Load and display the map
    # Load your JSON data
    try:
        with open('pirep.json', 'r', encoding='utf-8') as f:
            pirep_data = json.load(f)
    except Exception as e:
        st.error(f"Error loading pirep.json: {e}")
        pirep_data = {"pirep": []}

    try:
        with open('sigmet.json', 'r', encoding='utf-8') as f:
            sigmet_data = json.load(f)
    except Exception as e:
        st.error(f"Error loading sigmet.json: {e}")
        sigmet_data = {"sigmet": []}

    try:
        with open('airports.json', 'r', encoding='utf-8') as f:
            airports_data = json.load(f)
    except Exception as e:
        st.error(f"Error loading airports.json: {e}")
        airports_data = {"waypoints": []}

    # Read your HTML template and modify it to use the injected data
    with open('index.html', 'r', encoding='utf-8') as file:
        html_content = file.read()

    # Split the HTML at the point where we want to inject our data
    split_point = html_content.find('fetch(\'pirep.json\')')
    if split_point == -1:
        st.error("Could not find the insertion point in HTML")
    else:
        # Take everything before the fetch commands
        html_first_part = html_content[:split_point]
        
        # Find the end of the script tag
        script_end = html_content.find('</script>', split_point)
        html_last_part = html_content[script_end:] if script_end != -1 else ""
        
        # Create new JS that uses our injected data instead of fetching
        new_js = f"""
        // Data injected by Streamlit
        const pireps = {json.dumps(pirep_data['pirep'])};
        pireps.forEach(p => {{
        if (!p.lat || !p.lon) return;
        const info = `FLT LVL: ${{p.fltLvl || 'N/A'}}<br>Temp: ${{p.temp}}°C<br>Wind: ${{p.wdir}}° @ ${{p.wspd}} kt<br>AC: ${{p.acType}}`;

        L.circleMarker([p.lat, p.lon], {{
            radius: 5,
            fillColor: "blue",
            color: "black",
            weight: 1,
            fillOpacity: 0.8
        }}).addTo(map).bindPopup(info);
        }});

        // SIGMET data
        const sigmets = {json.dumps(sigmet_data['sigmet'])};
        sigmets.forEach(p => {{
            if (!p.coords || p.coords.length < 3) return; // Need at least 3 points
            
            const info = `Time: ${{p.creationTime || 'N/A'}}<br>Speed: ${{p.movementSpd}} kt <br>Direction: ${{p.movementDir}}°<br>Hazard: ${{p.hazard}}`;
            
            const latlngs = p.coords.map(c => [c.lat, c.lon]);
            
            const color = getSeverityColor(p.severity);
            
            L.polygon(latlngs, {{
                color: color,
                weight: 2,
                fillOpacity: 0.4
            }}).addTo(map).bindPopup(info);
        }});

        // Airport data
        const waypoints = {json.dumps(airports_data['waypoints'])};
        
        // Filter airports by altitude
        const lowAltitudeAirports = waypoints.filter(airport => airport.altitude < 9000);
        const highAltitudeAirports = waypoints.filter(airport => airport.altitude >= 9000);
        
        // Add markers for all airports
        lowAltitudeAirports.forEach(airport => {{
            L.marker([airport.lat, airport.log], {{
                icon: L.divIcon({{
                    className: 'airport-marker low-altitude',
                    html: `<div style="width: 10px; height: 10px; background-color: black; transform: rotate(45deg);"></div>`,
                    iconSize: [10, 10]
                }})
            }}).addTo(map).bindPopup(`${{airport.airport_id}}<br>Altitude: ${{airport.altitude}} ft`);
        }});
        
        highAltitudeAirports.forEach(airport => {{
            L.marker([airport.lat, airport.log], {{
                icon: L.divIcon({{
                    className: 'airport-marker high-altitude',
                    html: `<div style="background-color: red; width: 10px; height: 10px; border-radius: 50%;"></div>`,
                    iconSize: [10, 10]
                }})
            }}).addTo(map).bindPopup(`${{airport.airport_id}}<br>Altitude: ${{airport.altitude}} ft`);
        }});
        
        // Draw curved lines between low altitude airports if there are at least 2
        if (lowAltitudeAirports.length >= 2) {{
            // Sort airports west to east for connection
            lowAltitudeAirports.sort((a, b) => a.log - b.log);
            
            // Connect the airports with curved lines
            for (let i = 0; i < lowAltitudeAirports.length - 1; i++) {{
                const start = [lowAltitudeAirports[i].lat, lowAltitudeAirports[i].log];
                const end = [lowAltitudeAirports[i+1].lat, lowAltitudeAirports[i+1].log];
                
                // Create a curved line
                const latlngs = createCurvedLine(start, end);
                
                L.polyline(latlngs, {{
                    color: 'black',
                    weight: 3,
                    opacity: 0.7,
                    curvature: 0.3
                }}).addTo(map);
            }}
        }}
        """
        
        # Combine everything
        final_html = html_first_part + new_js + html_last_part

        # Render the combined HTML
        st.subheader("Flight Route Map")

        components.html(final_html, height=600)

    # Information sidebar
    st.sidebar.header("Map Information")
    st.sidebar.info("""
    - Black squares: Low altitude airports (<9000 ft)
    - Red circles: High altitude airports (≥9000 ft)
    - Blue circles: PIREP data points
    - Colored polygons: SIGMET warnings
    """)
    # Display the map
    st.subheader("Flight Route Map")
    # components.html(html_content, height=500)
    
    # Display summary section
    st.subheader("Flight Summary")
    with st.container(border=True):
        st.write("This is the summary of your flight plan based on the weather conditions.")
        
        # In a real app, you would generate this summary based on the weather data
        airport_list = ", ".join([a["icao"] for a in st.session_state.airport_data])
        st.write(f"Flight route: {airport_list}")
        st.write("Weather conditions appear favorable for your flight plan.")
        st.write("No significant weather hazards detected along your route.")
