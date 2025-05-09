import streamlit as st
import streamlit.components.v1 as components
import json
import uuid
from helper import * 


def get_dropdown_styles(color_name):
    colors = [{"primary": "#28a745","light": "#d4edda"},{"primary": "#ffc107","light": "#fff3cd"},{"primary": "#fd7e14","light": "#ffe5b4"},{"primary": "#dc3545","light": "#f8d7da"},{"primary": "#6c757d","light": "#f1f3f5"}]
    print(color_name)
    print(type(color_name))
    return colors[color_name-1]

st.set_page_config(layout="wide", page_title="Flight Weather Planning Tool")

airports=[]
st.title("Flight Weather Planning Tool")

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
if 'report' not in st.session_state:
    st.session_state.report = ''


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

if st.button("Submit"):
    for airport in st.session_state.airports:
        airport["icao"] = st.session_state[f"icao_{airport['id']}"]
        airport["altitude"] = st.session_state[f"alt_{airport['id']}"]


        lat, lon= lat_log(airport["icao"])
        airports.append({
        "airport_id": airport["icao"],
        "altitude": airport["altitude"],
        "lat": lat,
        "lon": lon,
        "warning_level": warning_level(airport["icao"])
        })

    output_data = {"waypoints": airports}
    with open("airports_st.json", "w") as f:
        json.dump(output_data, f, indent=2)
    
    st.session_state.airport_data = []
    for airport in st.session_state.airports:
        if airport["icao"]:
            k = parse_metar(airport["icao"])
            l = get_formatted_taf(airport["icao"])
            mock_data = {
                "icao": airport["icao"],
                "altitude": airport["altitude"],
                "metar":k,
                "taf": l,
                "warning_level": warning_level(airport["icao"])
            }
            st.session_state.report += '\n'
            st.session_state.report += k
            st.session_state.report += '\n'
            st.session_state.report += l
            st.session_state.airport_data.append(mock_data)
            
            
    
    st.session_state.submitted = True
    st.rerun()

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
                style = get_dropdown_styles(airport["warning_level"])
                st.markdown(f"""
                                <style>
                                .custom-expander > summary {{
                                    background-color: {style['primary']};
                                    color: white;
                                    padding: 10px;
                                    border-radius: 10px;
                                    cursor: pointer;
                                    font-size: 18px;
                                    font-weight: bold;
                                }}

                                .custom-expander[open] > summary {{
                                    border-bottom-left-radius: 0;
                                    border-bottom-right-radius: 0;
                                }}

                                .custom-expander {{
                                    border: 2px solid {style['primary']};
                                    border-radius: 10px;
                                    margin-bottom: 1rem;
                                }}
                                </style>
                            """, unsafe_allow_html=True)

                st.markdown(f"""
                            <details class="custom-expander">
                            <summary>METAR</summary>
                            <div style='padding: 15px; color: black; background-color: {style['light']}; border-top: 2px solid {style['primary']};'>
                                <p>{airport['metar'].replace('\n', '<br>')}</p>
                            </div>
                            </details>
                            """, unsafe_allow_html=True)
    
    taf_cols = st.columns(num_airports)
    for i, col in enumerate(taf_cols):
        if i < len(st.session_state.airport_data):
            airport = st.session_state.airport_data[i]
            with col:
                style = get_dropdown_styles(airport["warning_level"])
                st.markdown(f"""
                                <style>
                                .custom-expander > summary {{
                                    background-color: {style['primary']};
                                    color: white;
                                    padding: 10px;
                                    border-radius: 10px;
                                    cursor: pointer;
                                    font-size: 18px;
                                    font-weight: bold;
                                }}

                                .custom-expander[open] > summary {{
                                    border-bottom-left-radius: 0;
                                    border-bottom-right-radius: 0;
                                }}

                                .custom-expander {{
                                    border: 2px solid {style['primary']};
                                    border-radius: 10px;
                                    margin-bottom: 1rem;
                                }}
                                </style>
                            """, unsafe_allow_html=True)
                st.markdown(f"""
                            <details class="custom-expander">
                            <summary>TAF</summary>
                            <div style='padding: 15px;color: black; background-color: {style['light']}; border-top: 2px solid {style['primary']};'>
                                <p>{airport['taf'].replace('\n', '<br>')}</p>
                            </div>
                            </details>
                            """, unsafe_allow_html=True) ##########


    x=generate_quick('airports_st.json')
        


    

    with open('pireps.json', 'r', encoding='utf-8') as f:
        pirep_data = json.load(f)
    if not pirep_data.get('pireps'):
        st.warning("No significant PIREPs found near the flight path.")
        
    with open('route_weather.json', 'r', encoding='utf-8') as f:
        route_weather_data = json.load(f)

    if not route_weather_data.get('warnings'):
            st.warning("No significant weather conditions detected near the flight path.")


    sigmet_json_generator('airports_st.json')
    with open('sigmets_new.json', 'r', encoding='utf-8') as f:
        sigmet_data = json.load(f)


    with open('airports_st.json', 'r', encoding='utf-8') as f:
        airports_data = json.load(f)


    with open('index.html', 'r', encoding='utf-8') as file:
        html_content = file.read()

    split_point = html_content.find('////hellow olrd')
    if split_point == -1:
        split_point = html_content.find('var map = L.map')  # Try to find map initialization
        if split_point == -1:
            st.error("Could not find the insertion point in HTML")
            split_point = len(html_content)

    html_first_part = html_content[:split_point]

    html_last_part = html_content[split_point:]


    new_js = f"""
        // Function to create a slightly upward curved line between two points
        function createCurvedLine(startPoint, endPoint) {{
            const latlngs = [];
            const points = 20; // Number of points to create a smooth curve
            
            // Calculate control point (for upward curve)
            const midLat = (startPoint[0] + endPoint[0]) / 2;
            const midLon = (startPoint[1] + endPoint[1]) / 2;
            const distance = Math.sqrt(
                Math.pow(endPoint[0] - startPoint[0], 2) + 
                Math.pow(endPoint[1] - startPoint[1], 2)
            );
            
            // Make the curve higher for longer distances
            const curveHeight = distance * 0.15;
            
            // Create a quadratic Bezier curve
            for (let i = 0; i <= points; i++) {{
                const t = i / points;
                const lat = (1-t)*(1-t)*startPoint[0] + 
                            2*(1-t)*t*(midLat + curveHeight) + 
                            t*t*endPoint[0];
                const lon = (1-t)*(1-t)*startPoint[1] + 
                            2*(1-t)*t*midLon + 
                            t*t*endPoint[1];
                latlngs.push([lat, lon]);
            }}
            return latlngs;
        }}

        function getSeverityColor(severity) {{
            if (severity === 0) return "gray";
            if (severity <= 2) return "yellow";
            if (severity <= 4) return "orange";
            if (severity === 5) return "red";
            return "blue"; // fallback
        }}


        // PIREP data
        const pireps = {json.dumps(pirep_data.get('pireps', []))};
        pireps.forEach(p => {{
            if (!p.lat || !p.lon) return;
            const info = `${{p.summary || 'N/A'}}`;
            L.circleMarker([p.lat, p.lon], {{
                radius: 5,
                fillColor: "blue",
                color: "black",
                weight: 1,
                fillOpacity: 0.8
            }}).addTo(map).bindPopup(info);
        }});

        // Route weather warnings
        const warnings = {json.dumps(route_weather_data.get('warnings', []))};
        warnings.forEach(p => {{
            if (!p.lat || !p.lon) return;
            const info = `Description: ${{p.description || 'N/A'}}<br>Temp: ${{p.temperature}}°C<br>Windspeed: ${{p.windspeed}}kt<br>code: ${{p.code}}`;
            L.circleMarker([p.lat, p.lon], {{
                radius: 7,
                fillColor: "purple",
                color: "purple",
                weight: 1,
                fillOpacity: 0.8
            }}).addTo(map).bindPopup(info);
        }});

        // SIGMET data
        const sigmets = {json.dumps(sigmet_data.get('sigmet', []))};
        sigmets.forEach(p => {{
            if (!p.coords || p.coords.length < 3) return;
            const info = `${{p.sigmet_eng || 'N/A'}}`;
            const latlngs = p.coords.map(c => [c.lat, c.lon]);
            const c = getSeverityColor(p.severity);
            L.polygon(latlngs, {{
                color: c,
                weight: 2,
                fillOpacity: 0.4
            }}).addTo(map).bindPopup(info);
        }});

        // Airport data
        const waypoints = {json.dumps(airports_data.get('waypoints', []))};
        const allAirports = [...waypoints];

        // Add markers and circles for airports
        allAirports.forEach(airport => {{
            // Marker
            L.marker([airport.lat, airport.lon]).addTo(map).bindPopup(`${{airport.airport_id}}<br>Altitude: ${{airport.altitude}} ft`);
            
            // Circle for flight rules
            const warningLevel = airport.warning_level || 5;
            let circleColor = 'grey';
            let circleLabel = 'UNKNOWN';
            
            switch(warningLevel) {{
                case 1: circleColor = '#00FF00'; circleLabel = 'VFR'; break;
                case 2: circleColor = '#FFFF00'; circleLabel = 'MVFR'; break;
                case 3: circleColor = '#FF9900'; circleLabel = 'IFR'; break;
                case 4: circleColor = '#FF0000'; circleLabel = 'LIFR'; break;
            }}
            
            L.circle([airport.lat, airport.lon], {{
                color: circleColor,
                fillColor: circleColor,
                fillOpacity: 0.2,
                radius: 50000,
                weight: 1
            }}).addTo(map).bindTooltip(circleLabel);
        }});

        // Draw curved lines between low altitude airports
        const lowAltitudeAirports = allAirports.filter(a => a.altitude < 9000);
        if (lowAltitudeAirports.length >= 2) {{
            lowAltitudeAirports.sort((a, b) => a.lon - b.lon);
            for (let i = 0; i < lowAltitudeAirports.length - 1; i++) {{
                const start = [lowAltitudeAirports[i].lat, lowAltitudeAirports[i].lon];
                const end = [lowAltitudeAirports[i+1].lat, lowAltitudeAirports[i+1].lon];
                const latlngs = createCurvedLine(start, end);
                L.polyline(latlngs, {{
                    color: 'black',
                    weight: 3,
                    opacity: 0.7
                }}).addTo(map);
            }}
        }}
    """

    final_html = html_first_part + new_js + html_last_part

    st.subheader("Flight Route Map")
    components.html(final_html, height=600, scrolling=True)


    
    st.sidebar.header("Map Information")
    st.sidebar.info("""
    - Markers: All Airports
    - Blue circles: PIREP data points
    - Colored polygons: SIGMET warnings
    - Yellow circles: en-route warnings
    """)
    st.subheader("Flight Route Map")
    st.sidebar.header("KEY VALUES")
    st.sidebar.info("""
    - VFR: GREEN
    - MFR: YELLOW
    - IFR: ORANGE
    - LIFR: RED
    - UNKOWN: GREY 
                    """)
    
    
    st.subheader("Flight Summary")
    with st.container(border=True):
        final = summary()
        st.markdown(
        f"""
        <div style="background-color: #E3F2FD; padding: 15px; border-radius: 10px; color: #0D47A1; font-family: 'Courier New', monospace;">
        <pre style="white-space: pre-wrap; word-wrap: break-word;">{final}</pre>
        </div>
        """,
        unsafe_allow_html=True
        )

