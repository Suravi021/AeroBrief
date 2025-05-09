import re
import requests
from groq import Groq
import json
from datetime import datetime, timezone
from geopy.distance import geodesic
import numpy as np
import time

import os
from dotenv import load_dotenv



abbreviations = {
    "ABV": "above",
    "CNL": "cancelled",
    "CTA": "control area",
    "FCST": "forecast",
    "FIR": "Flight Information Region",
    "FL": "flight level",
    "FT": "feet",
    "INTSF": "intensifying",
    "KT": "knots",
    "KMH": "kilometres per hour",
    "M": "meters",
    "MOV": "moving",
    "NC": "no change",
    "NM": "nautical miles",
    "OBS": "observed",
    "SFC": "surface",
    "STNR": "stationary",
    "TOP": "top of cloud",
    "WI": "within",
    "WKN": "weakening",
    "Z": "UTC",
}

weather_codes = {
    "AREA TS": "Area-wide thunderstorms",
    "LINE TS": "Thunderstorm line",
    "EMBD TS": "Embedded thunderstorms",
    "TDO": "Tornado",
    "FC": "Funnel Cloud",
    "WTSPT": "Waterspout",
    "HVY GR": "Heavy hail",
    "OBSC TS": "Obscured thunderstorms",
    "EMBD TSGR": "Embedded thunderstorms with hail",
    "FRQ TS": "Frequent thunderstorms",
    "SQL TS": "Squall line thunderstorms",
    "FRQ TSGR": "Frequent thunderstorms with hail",
    "SQL TSGR": "Squall line thunderstorms with hail",
    "SEV TURB": "Severe turbulence",
    "SEV ICE": "Severe icing",
    "SEV ICE (FZRA)": "Severe icing due to freezing rain",
    "SEV MTW": "Severe mountain wave",
    "HVY DS": "Heavy duststorm",
    "HVY SS": "Heavy sandstorm",
    "RDOACT CLD": "Radioactive cloud"
}
taf_dict = {
    "SKC": "Sky clear",
    "NSC": "No significant clouds",
    "FEW": "Few clouds (1/8 - 2/8)",
    "SCT": "Scattered clouds (3/8 - 4/8)",
    "BKN": "Broken clouds (5/8 - 7/8)",
    "OVC": "Overcast (8/8)",
    "SN": "Snow",
    "RA": "Rain",
    "BR": "Mist",
    "FG": "Fog",
    "HZ": "Haze",
    "-": "Light",
    "+": "Heavy",
    "VC": "In the vicinity",
    "SH": "Showers",
    "TS": "Thunderstorms",
    "DZ": "Drizzle",
    "FM": "From",
    "TEMPO": "Temporary",
    "PROB30": "30% probability",
    "PROB40": "40% probability",
    "P6SM": "Visibility greater than 6 statute miles",
    "VV///": "Vertical visibility unknown",
}

def is_point_in_polygon(x, y, polygon):
    inside = False
    n = len(polygon)
    j = n - 1  

    for i in range(n):
        xi, yi = polygon[i]["lat"], polygon[i]["lon"]
        xj, yj = polygon[j]["lat"], polygon[j]["lon"]
        
        if ((yi > y) != (yj > y)):
            x_intersect = (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
            if x < x_intersect:
                inside = not inside
        j = i

    return inside


def get_formatted_taf(airport_code):
    url = f"https://aviationweather.gov/api/data/taf?ids={airport_code}&format=json"
    response = requests.get(url)
    
    
    if not response.json():
        return f"No TAF data available for airport '{airport_code}'."
    data = response.json()
    
    taf_raw = data[0].get("rawTAF", "")
    if not taf_raw:
        return f"TAF data for '{airport_code}' is missing raw text."

    taf_dict = {
        "SKC": "Sky clear",
        "NSC": "No significant clouds",
        "FEW": "Few clouds (1/8 - 2/8)",
        "SCT": "Scattered clouds (3/8 - 4/8)",
        "BKN": "Broken clouds (5/8 - 7/8)",
        "OVC": "Overcast (8/8)",
        "SN": "Snow",
        "RA": "Rain",
        "BR": "Mist",
        "FG": "Fog",
        "HZ": "Haze",
        "-": "Light",
        "+": "Heavy",
        "VC": "In the vicinity",
        "SH": "Showers",
        "TS": "Thunderstorms",
        "DZ": "Drizzle",
        "FM": "From",
        "TEMPO": "Temporary",
        "PROB30": "30% probability",
        "PROB40": "40% probability",
        "P6SM": "Visibility greater than 6 statute miles",
        "VV///": "Vertical visibility unknown",
    }

    def decode_wind(wind_str):
        match = re.match(r"(\d{3})(\d{2,3})(G\d{2,3})?KT", wind_str)
        if match:
            direction, speed, gust = match.groups()
            wind = f"Wind from {direction}° at {speed} knots"
            if gust:
                wind += f" with gusts to {gust[1:]} knots"
            return wind
        return None

    words = taf_raw.split()
    result = [f"Decoded TAF Forecast:", f"- Station: {airport_code.upper()}"]
    segments = []
    current_segment = []

    for word in words:
        if re.match(r"\d{6}Z", word):  # issuance time
            dt = datetime.now(timezone.utc)
            try:
                day, hour, minute = int(word[:2]), int(word[2:4]), int(word[4:6])
                dt = datetime(dt.year, dt.month, day, hour, minute)
            except Exception:
                pass
            result.append(f"- Issued: {dt.strftime('%Y-%m-%d %H:%MZ')}")
        elif re.match(r"\d{4}/\d{4}", word):  # validity
            start, end = word.split("/")
            result.append(f"- Valid Period: From {start[:2]}th at {start[2:]}Z to {end[:2]}th at {end[2:]}Z")
        elif word.startswith("FM") and len(word) >= 7:
            if current_segment:
                segments.append(current_segment)
            current_segment = [f"• From {word[2:4]}th at {word[4:6]}:{word[6:]}Z"]
        elif word in taf_dict:
            current_segment.append(f"– {taf_dict[word]}")
        elif word.startswith("TEMPO") or word.startswith("BECMG") or word.startswith("PROB"):
            if current_segment:
                segments.append(current_segment)
            label = taf_dict.get(word, word)
            current_segment = [f"• {label}"]
        elif decode_wind(word):
            current_segment.append(f"– {decode_wind(word)}")
        elif re.match(r"\d{4}SM", word):
            current_segment.append(f"– Visibility: {int(word[:4]) / 100.0} statute miles")
        else:
            # maybe a cloud code like SCT020
            cloud_match = re.match(r"([A-Z]{3})(\d{3})", word)
            if cloud_match:
                code, altitude = cloud_match.groups()
                meaning = taf_dict.get(code, code)
                current_segment.append(f"– {meaning} at {int(altitude)*100} ft")
    
    if current_segment:
        segments.append(current_segment)

    result.append("- Forecast Segments:")
    for seg in segments:
        result.extend(["  " + line for line in seg])

    return "\n".join(result)


def fetch_pirep(airport_id):
    url = f"https://aviationweather.gov/api/data/pirep?ids={airport_id}&format=json"
    response1 = requests.get(url)
    response1=response1.json()
    return response1

def fetch_sigmet_h(altitude=None):
    final = ""
    
    with open('sigmets_new.json', 'r') as file:
        data = json.load(file)
    data = data["sigmet"]

    with open('airports_st.json', 'r') as file:
        airports = json.load(file)
    airports = airports['waypoints']

    for airport in airports:

        for sigmet in data:
            if is_point_in_polygon(airport['lat'], airport['lon'], sigmet['coords']):
                final += sigmet['sigmet_eng']
                final += '\n'
                
    return final


def fetch_metar(airport_id):
    url = f"https://aviationweather.gov/api/data/metar?ids={airport_id}&format=json"
    response = requests.get(url)
    return response.json()

def parse_metar(airport_id,yes=0):
    metar_list = fetch_metar(airport_id)

    if not metar_list or not isinstance(metar_list, list):
        return f"No valid METAR data returned for {airport_id}."

    metar_entry = metar_list[0]  

    if yes:
        return metar_entry['rawOb']

    result = {}

    result["Type"] = "Routine METAR report" if metar_entry.get("metarType") == "METAR" else "Special METAR report"
    result["Station"] = metar_entry.get("icaoId", "Unknown")
    result["Time"] = metar_entry.get("reportTime", "Unknown")

    wdir = metar_entry.get("wdir")
    wspd = metar_entry.get("wspd")
    wgst = metar_entry.get("wgst")
    if wdir is not None and wspd is not None:
        wind = f"{wdir}° at {wspd} knots"
        if wgst:
            wind += f" with gusts to {wgst} knots"
        result["Wind"] = wind

    vis = metar_entry.get("visib")
    if vis is not None:
        result["Visibility"] = f"{vis} statute miles"

    wx = metar_entry.get("wxString")
    if wx:
        result["Weather"] = wx

    clouds = metar_entry.get("clouds", [])
    if clouds:
        layers = []
        cover_dict = {
            "FEW": "Few clouds",
            "SCT": "Scattered clouds",
            "BKN": "Broken clouds",
            "OVC": "Overcast"
        }
        for cloud in clouds:
            cover = cloud.get("cover")
            base = cloud.get("base")
            if cover and base is not None:
                desc = f"{cover_dict.get(cover, cover)} at {base * 100} feet"
                layers.append(desc)
        result["Sky"] = "; ".join(layers)

    temp = metar_entry.get("temp")
    dewp = metar_entry.get("dewp")
    if temp is not None:
        result["Temperature"] = f"{temp:.1f}°C"
    if dewp is not None:
        result["Dewpoint"] = f"{dewp:.1f}°C"

    alt = metar_entry.get("altim")
    if alt is not None:
        result["Altimeter"] = f"{alt} hPa"

    slp = metar_entry.get("slp")
    if slp is not None:
        result["Sea Level Pressure"] = f"{slp} hPa"

    final = "\nDecoded METAR Report:\n"
    for key, value in result.items():
        final += f"{key} {value}\n"

    return final
    

def fetch_metar_new(airport_ids):
    if isinstance(airport_ids, list):
        airport_id = ''
        for id in airport_ids:
            airport_id += id
            airport_id += '%'
        airport_id = airport_id[:-1]
    else:
        airport_id = airport_ids
        airport_ids = ''

    url = f"https://aviationweather.gov/api/data/metar?ids={airport_id}&format=json&taf=true"
    x = requests.get(url)
    try:
        response = x.json()
        n = len(airport_ids)
        metar_taf = {}
        if n == 0:
            # #print(response)
            return parse_metar_new(response[0]['rawOb'])
        for x in range(n):
            airport_data = response[x]
            # #print(airport_data)
            metar_taf[airport_data['icaoId']] = {
                # 'taf': parse_taf(airport_data['rawTaf']),
                'metar': parse_metar_new(airport_data['rawOb'])
            }        
        return metar_taf
    except:
        print(x)

def parse_metar_new(raw):
    components = raw.split()
    result = {}

    i = 0
    if components[i] in ["METAR", "SPECI"]:
        result["Type"] = "Routine METAR report" if components[i] == "METAR" else "Special METAR report"
    else:
        result["Type"] = 'METAR'

    result["Station"] = components[i]
    i += 1

    #time
    time_match = re.match(r"(\d{2})(\d{2})(\d{2})Z", components[i])
    if time_match:
        day, hour, minute = time_match.groups()
        result["Time"] = f"{day}th at {hour}:{minute} UTC"
    i += 1

    #wind
    wind_match = re.match(r"(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT", components[i])
    if wind_match:
        direction, speed, gust = wind_match.groups()
        direction_text = "Variable" if direction == "VRB" else f"{direction}°"
        wind_desc = f"{direction_text} at {int(speed)} knots"
        if gust:
            wind_desc += f" with gusts to {int(gust[1:])} knots"
        result["Wind"] = wind_desc
    i += 1

    # Visibility
    if "SM" in components[i]:
        result["Visibility"] = f"{components[i].replace('SM', '')} statute miles"
        i += 1

    wx_dict = {
        "-SN": "Light snow",
        "SN": "Moderate snow",
        "+SN": "Heavy snow",
        "RA": "Rain",
        "-RA": "Light rain",
        "+RA": "Heavy rain",
        "BR": "Mist",
        "FG": "Fog",
        "HZ": "Haze"
    }
    if re.match(r"[-+A-Z]{2,}", components[i]):
        result["Weather"] = wx_dict.get(components[i], components[i])
        i += 1

    # Sky condition
    sky_match = re.match(r"(FEW|SCT|BKN|OVC)(\d{3})", components[i])
    if sky_match:
        cover, height = sky_match.groups()
        cover_dict = {
            "FEW": "Few clouds",
            "SCT": "Scattered clouds",
            "BKN": "Broken clouds",
            "OVC": "Overcast"
        }
        result["Sky"] = f"{cover_dict.get(cover)} at {int(height)*100} feet"
        i += 1

    # Temperature and dew point
    temp_dew = components[i]
    if '/' in temp_dew:
        temp, dew = temp_dew.split('/')
        result["Temperature"] = f"{int(temp)}°C" if 'M' not in temp else f"-{int(temp[1:])}°C"
        result["Dewpoint"] = f"{int(dew)}°C" if 'M' not in dew else f"-{int(dew[1:])}°C"
        i += 1

    # Altimeter
    if components[i].startswith("A"):
        alt = components[i][1:]
        result["Altimeter"] = f"{alt[:2]}.{alt[2:]} inHg"
        i += 1

    # Remarks
    if "RMK" in components[i:]:
        rmk_index = components.index("RMK")
        rmk_parts = components[rmk_index+1:]

        for part in rmk_parts:
            if part.startswith("SLP"):
                result["Sea Level Pressure"] = f"{part[3:]} hPa"
            if part.startswith("T"):
                temp = int(part[1:5])
                dew = int(part[5:])
                t_sign = '-' if part[0] == '1' else ''
                d_sign = '-' if part[5] == '1' else ''
                result["Exact Temperature"] = f"{t_sign}{temp/10:.1f}°C"
                result["Exact Dewpoint"] = f"{d_sign}{dew/10:.1f}°C"

    # Format output
    final = ""
    # #print("\nDecoded METAR Report:\n")
    for key, value in result.items():
        final += key
        final += ' '
        final += value
        final += "\n" 
        # #print(f"{key}: {value}")
    return final

def read_pirep(file_path):
    final=''
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    pireps = data.get("pireps", [])
    if len(pireps) !=0:
        for pirep in pireps:
            final += pirep["summary"] + ' '

    ##print('final, pirep', final)
    return final

def summary():
    load_dotenv()
    try:
        final=''
        with open("airports_st.json", "r") as f:
            data = json.load(f)


        for waypoint in data["waypoints"]:
            air = waypoint["airport_id"]
            final += fetch_metar_new(air)
            final += get_formatted_taf(air)

        final += fetch_sigmet_h()
        final += read_pirep('pireps.json')
    except:
        final = "give me the breifing of the weather in KLAX airport"

    try: 
        api = os.getenv("GROQ_API")
        client = Groq(api_key=api)
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{
                "role":"system", "content": "You brief pilots on the weather and give them the import details of their flight plan DO NOT SAY ANYTHING EXTRA"
            },
            {
                "role":"user", "content": final
            }],
            temperature=1,
            max_completion_tokens=8192,
            top_p=1,
            stream=False,
            stop=None,
        )

        

        return completion.choices[0].message.content
    except:
        return 'there was an error'

def warning_level(airport_id):
    raw_metar = parse_metar(airport_id, 1) 
    visibility = None
    ceiling = None
    ceiling_layers = []
 
    parts = raw_metar.strip().split()
 
    for i, part in enumerate(parts):
        if "SM" in part:
            vis_str = part.replace("SM", "")
            try:
                visibility = float(vis_str)
            except ValueError:
                try:
                    if "/" in vis_str:
                        num, denom = vis_str.split("/")
                        visibility = float(num) / float(denom)
                except:
                    pass
        elif i < len(parts) - 1 and parts[i+1] == "SM":
            vis_parts = []
            j = i
            while j >= 0:
                if parts[j][0].isdigit() or "/" in parts[j]:
                    vis_parts.insert(0, parts[j])
                    j -= 1
                else:
                    break
 
            if len(vis_parts) == 1:
                try:
                    visibility = float(vis_parts[0])
                except:
                    pass
            elif len(vis_parts) == 2:
                try:
                    whole = float(vis_parts[0])
                    frac = vis_parts[1]
                    num, denom = frac.split("/")
                    frac_val = float(num) / float(denom)
                    visibility = whole + frac_val
                except:
                    pass
 
        cloud_types = ["SKC", "CLR", "NSC", "NCD", "FEW", "SCT", "BKN", "OVC"]
 
        for cloud_type in cloud_types:
            if part.startswith(cloud_type) and len(part) > len(cloud_type):
                height_str = part[len(cloud_type):]
                if height_str.isdigit():
                    height = int(height_str) * 100  # Convert to feet
                    ceiling_layers.append((cloud_type, height))
 
    for layer_type, height in ceiling_layers:
        if layer_type in ["BKN", "OVC"]:
            if ceiling is None or height < ceiling:
                ceiling = height
 
    if ceiling is None and visibility is None:
        flight_category = "UNKNOWN"
    else:
        ceiling_value = ceiling if ceiling is not None else float('inf')
        visibility_value = visibility if visibility is not None else float('inf')
 
        if ceiling_value < 500 or visibility_value < 1:
            flight_category = "LIFR" 
        elif (ceiling_value < 1000) or (visibility_value < 3):
            flight_category = "IFR"  
        elif (ceiling_value <= 3000) or (visibility_value <= 5):
            flight_category = "MFR"  
        else:
            flight_category = "VFR"   
 
    d = {"VFR": 1, "MFR":2, "IFR": 3, "LIFR": 4, "UNKNOWN": 5}
    return d[flight_category]


weather_code_descriptions = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm: Slight or moderate",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}

severe_weather_codes = {3,81,82, 86, 95, 96, 99,45, 48,51, 53, 55,56, 57,61, 63, 65,66, 67,71, 73, 75,77,80,85}


def summarize_pirep(raw):
    if not raw or not isinstance(raw, str):
        return "No PIREP information available."

    summary = []

    if re.search(r"\bUUA\b", raw):
        summary.append("⚠️ Urgent PIREP issued – hazardous conditions reported")

    fl_match = re.search(r"/FL(\d+)", raw)
    if fl_match:
        alt = int(fl_match.group(1)) * 100
        summary.append(f"Altitude: {alt} ft")

    tp_match = re.search(r"/TP\s*([A-Z0-9\-]+)", raw)
    if tp_match:
        summary.append(f"Aircraft type: {tp_match.group(1)}")

    tops = re.search(r"TOPS\s+(\d+)", raw)
    bases = re.search(r"BASES\s+(\d+)", raw)
    if tops and bases:
        summary.append(f"Cloud tops at {int(tops.group(1)) * 100} ft, bases at {int(bases.group(1)) * 100} ft")
    elif tops:
        summary.append(f"Cloud tops at {int(tops.group(1)) * 100} ft")
    elif bases:
        summary.append(f"Cloud bases at {int(bases.group(1)) * 100} ft")

    ov_match = re.search(r"/OV\s+([A-Z0-9]+)", raw)
    if ov_match:
        summary.append(f"Reported over: {ov_match.group(1)}")

    tm_match = re.search(r"/TM\s+(\d{4})", raw)
    if tm_match:
        summary.append(f"Report time: {tm_match.group(1)} Z")

    tb_match = re.search(r"/TB\s+(.+?)(?=\s*/|$)", raw)
    if tb_match:
        summary.append(f"Turbulence reported: {tb_match.group(1).strip()}")

    ic_match = re.search(r"/IC\s+(.+?)(?=\s*/|$)", raw)
    if ic_match:
        summary.append(f"Icing reported: {ic_match.group(1).strip()}")

    wx_match = re.search(r"/WX\s+([\w\s\-]+)", raw)
    if wx_match:
        summary.append(f"Weather: {wx_match.group(1).strip()}")

    return "; ".join(summary) if summary else "Unable to summarize PIREP."

def interpolate_points(start, end, interval_nm=50):
    total_distance = geodesic(start, end).nm
    steps = max(2, int(total_distance // interval_nm) + 1)
    lats = np.linspace(start[0], end[0], steps)
    lons = np.linspace(start[1], end[1], steps)
    return list(zip(lats, lons))

def find_weather_warnings_between_airports(airport1_json, airport2_json, threshold_nm=50, output_filename="pireps.json"):

    try:
        lat1 = airport1_json["weather"][0]["metar"][0]["lat"]
        lon1 = airport1_json["weather"][0]["metar"][0]["lon"]
        lat2 = airport2_json["weather"][0]["metar"][0]["lat"]
        lon2 = airport2_json["weather"][0]["metar"][0]["lon"]
    except Exception as e:
        print("Error parsing airport coordinates:", e)
        return []

    route_points = interpolate_points((lat1, lon1), (lat2, lon2))
    x=fetch_weather_for_route_points(route_points, output_filename="route_weather.json")
    while(x==False):
        time.sleep(1)
    
    # Combine PIREPs from both airports
    pireps = []
    if "pirep" in airport1_json["weather"][0]:
        pireps.extend(airport1_json["weather"][0]["pirep"])
    if "pirep" in airport2_json["weather"][0]:
        pireps.extend(airport2_json["weather"][0]["pirep"])

    seen = set()
    warnings = []

    for pt in route_points:
        for pirep in pireps:
            try:
                pirep_lat = pirep["lat"]
                pirep_lon = pirep["lon"]
                distance = geodesic(pt, (pirep_lat, pirep_lon)).nm
                if distance <= threshold_nm:
                    unique_key = (
                        round(pt[0], 4), round(pt[1], 4),
                        round(pirep_lat, 4), round(pirep_lon, 4),
                        pirep.get("rawOb", "")
                    )
                    if unique_key not in seen:
                        seen.add(unique_key)
                        warnings.append({
                            "distance_to_pirep_nm": round(distance, 1),
                            "pirep_raw": pirep.get("rawOb", "No raw PIREP available"),
                            "summary": summarize_pirep(pirep.get("rawOb", "")),
                            "lat": pirep_lat, 
                            "lon": pirep_lon
                        })
            except:
                continue

    output_data = {"pireps": warnings}
    
    
    # Save to a JSON file
    with open(output_filename, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"✅ Saved {len(warnings)} unique weather warning points to {output_filename}")
    return True

def fetch_weather_for_route_points(route_points, output_filename="route_weather.json"):
    import requests
    import time

    weather_data = []

    for i, (lat, lon) in enumerate(route_points):
        try:
            response = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current_weather": True
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            weather = data.get("current_weather", {})
            code = weather.get("weathercode")
            description = weather_code_descriptions.get(code, "Unknown weather code")
            is_severe = code in severe_weather_codes

            if(is_severe):
                weather_data.append({
                "point_index": i,
                "lat": lat,
                "lon": lon,
                    "code": code,
                    "description": description,
                    "temperature": weather.get("temperature"),
                    "windspeed": weather.get("windspeed"),
                    "is_severe": is_severe
                
            })
            time.sleep(0.5)  
        except Exception as e:
            weather_data.append({
                "point_index": i,
                "lat": lat,
                "lon": lon,
                "error": str(e)
            })

    output_data = {"warnings": weather_data}

    with open(output_filename, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"✅ Saved weather data for {len(route_points)} points to {output_filename}")
    return True


def fetch_metar(airport_id):
    url = f"https://aviationweather.gov/api/data/metar?ids={airport_id}&format=json"
    response = requests.get(url)
    return response.json()

def fetch_taf(airport_id):
    url = f"https://aviationweather.gov/api/data/taf?ids={airport_id}&format=json"
    response = requests.get(url)
    
    return response.json()

def fetch_pirep(airport_id):
    url = f"https://aviationweather.gov/api/data/pirep?ids={airport_id}&format=json"
    response1 = requests.get(url)
    response1=response1.json()
    return response1


def lat_log(airport_id):
    url = f"https://aviationweather.gov/api/data/airport?ids={airport_id}&format=json"
    response = requests.get(url)
    response=response.json()
    coords = [response[0]['lat'],response[0]['lon']]
    return coords



def generate_quick(file_path):

    with open(file_path, 'r') as f:
        data = json.load(f)
    
    waypoints = data.get("waypoints", [])
    
    final_json_list=[]
    for waypoint in waypoints:
        airport_id = waypoint.get("airport_id")
        altitude=waypoint.get("altitude")
        output_airport_data={}
        weather_data = []
        pirep_dat=[]
        print(f"📍 Airport: {airport_id}]")
    
        metar = fetch_metar(airport_id)
        taf = fetch_taf(airport_id)
        pirep = fetch_pirep(airport_id)
        lat,log=lat_log(airport_id)

        weather_data.append({
            "airport_id": airport_id,
            "altitude": altitude,
            "lat":lat,
            "log":log,
            "metar": metar,
            "taf": taf,
            "pirep": pirep,
        })
        print("weather collected")
        
        output_airport_data={"weather": weather_data}

        final_json_list.append(output_airport_data)
        print("weather appended")

    x=find_weather_warnings_between_airports(final_json_list[0],final_json_list[-1])
    return x

abbreviations = {
    "ABV": "above",
    "CNL": "cancelled",
    "CTA": "control area",
    "FCST": "forecast",
    "FIR": "Flight Information Region",
    "FL": "flight level",
    "FT": "feet",
    "INTSF": "intensifying",
    "KT": "knots",
    "KMH": "kilometres per hour",
    "M": "meters",
    "MOV": "moving",
    "NC": "no change",
    "NM": "nautical miles",
    "OBS": "observed",
    "SFC": "surface",
    "STNR": "stationary",
    "TOP": "top of cloud",
    "WI": "within",
    "WKN": "weakening",
    "Z": "UTC",
}

weather_codes = {
    "AREA TS": "Area-wide thunderstorms",
    "LINE TS": "Thunderstorm line",
    "EMBD TS": "Embedded thunderstorms",
    "TDO": "Tornado",
    "FC": "Funnel Cloud",
    "WTSPT": "Waterspout",
    "HVY GR": "Heavy hail",
    "OBSC TS": "Obscured thunderstorms",
    "EMBD TSGR": "Embedded thunderstorms with hail",
    "FRQ TS": "Frequent thunderstorms",
    "SQL TS": "Squall line thunderstorms",
    "FRQ TSGR": "Frequent thunderstorms with hail",
    "SQL TSGR": "Squall line thunderstorms with hail",
    "SEV TURB": "Severe turbulence",
    "SEV ICE": "Severe icing",
    "SEV ICE (FZRA)": "Severe icing due to freezing rain",
    "SEV MTW": "Severe mountain wave",
    "HVY DS": "Heavy duststorm",
    "HVY SS": "Heavy sandstorm",
    "RDOACT CLD": "Radioactive cloud"
}

def fetch_sigmet(airport_id, altitude=None):

    base_url = "https://aviationweather.gov/api/data/airsigmet"
    params = {
        "format": "json"
    }
    if altitude:
        flight_level = int(altitude / 100)
        params["level"] = flight_level

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()

        try:
            print(response.json()[0]['rawAirSigmet'])
            return response.json()
            ##print(response.json())
        except ValueError:
            return {
                "error": "Response is not valid JSON",
                "raw": response.text
            }

    except requests.exceptions.RequestException as e:
        return {
            "error": "Request failed",
            "details": str(e)
        }


def parse_sigmet(text):
    output_lines = []

    sigmet_id = re.search(r'CONVECTIVE SIGMET (\d+[A-Z])', text)
    valid_until = re.search(r'VALID UNTIL (\d{4})Z', text)
    movement = re.search(r'MOV FROM (\d{3})(\d{2})KT', text)
    tops = re.search(r'TOPS TO FL(\d+)', text)
    area_match = re.search(r'FROM (.+?)DMSHG', text, re.DOTALL)
    outlook_time = re.search(r'OUTLOOK VALID (\d{6})-(\d{6})', text)
    outlook_area = re.search(r'OUTLOOK VALID.*?FROM (.+?)WST', text, re.DOTALL)


    if sigmet_id:
        output_lines.append(f"SIGMET ID: {sigmet_id.group(1)} (Convective, Central Region)")

    if valid_until:
        output_lines.append(f"Valid Until: {valid_until.group(1)} UTC")

    if area_match:
        area_points = area_match.group(1).strip().replace("\n", " ").split("-")
        output_lines.append("\nAffected Area (polygon points):")
        for point in area_points:
            output_lines.append(f" - {point.strip()}")

    if "DMSHG AREA TS" in text:
        output_lines.append("\nWeather: Area-wide thunderstorms (diminishing)")

    if movement:
        output_lines.append(f"Movement: From {movement.group(1)}° at {movement.group(2)} knots")

    if tops:
        output_lines.append(f"Cloud Tops: Up to FL{tops.group(1)} (approx. {int(tops.group(1)) * 100} ft)")

    if outlook_time and outlook_area:
        outlook_coords = outlook_area.group(1).strip().replace("\n", " ").split("-")
        output_lines.append(f"\nOutlook Forecast Time: {outlook_time.group(1)} UTC to {outlook_time.group(2)} UTC")
        output_lines.append("Forecast Area:")
        for point in outlook_coords:
            output_lines.append(f" - {point.strip()}")

    output_lines.append("\nAdditional SIGMETs may be issued. Refer to SPC for updates.")

    return "\n".join(output_lines)


def sigmet_json_generator(ap):
    with open(ap) as airports:
        ap = json.load(airports)

    sigmet=[]
    for a in ap['waypoints']:
        print(a['airport_id'])
        x=fetch_sigmet(a['airport_id'])
        coords=x[0]['coords']
        severity=x[0]['severity']
        print(coords)
        sigmet_english=parse_sigmet(x[0]['rawAirSigmet'])
        print(sigmet_english)
        

        sigmet.append({
            "sigmet_eng": sigmet_english,
            "coords": coords,
            "severity":severity
            })

        output_data = {"sigmet": sigmet}

        with open("sigmets_new.json", "w") as f:
            json.dump(output_data, f, indent=2)
