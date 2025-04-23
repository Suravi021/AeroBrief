import re
import requests

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

def parse_sigmet(text):
    # Extract SIGMET info
    sigmet_id = re.search(r'CONVECTIVE SIGMET (\d+[A-Z])', text)
    valid_until = re.search(r'VALID UNTIL (\d{4})Z', text)
    movement = re.search(r'MOV FROM (\d{3})(\d{2})KT', text)
    tops = re.search(r'TOPS TO FL(\d+)', text)
    area_match = re.search(r'FROM (.+?)DMSHG', text, re.DOTALL)
    outlook_time = re.search(r'OUTLOOK VALID (\d{6})-(\d{6})', text)
    outlook_area = re.search(r'OUTLOOK VALID.*?FROM (.+?)WST', text, re.DOTALL)

    print("SIGMET Report Summary\n----------------------")
    
    if sigmet_id:
        print(f"SIGMET ID: {sigmet_id.group(1)} (Convective, Central Region)")

    if valid_until:
        print(f"Valid Until: {valid_until.group(1)} UTC")

    if area_match:
        area_points = area_match.group(1).strip().replace("\n", " ").split("-")
        print("\nAffected Area (polygon points):")
        for point in area_points:
            print(f" - {point.strip()}")

    if "DMSHG AREA TS" in text:
        print("\nWeather: Area-wide thunderstorms (diminishing)")

    if movement:
        print(f"Movement: From {movement.group(1)}° at {movement.group(2)} knots")

    if tops:
        print(f"Cloud Tops: Up to {tops.group(1)} flight level (approx. {int(tops.group(1))*100} ft)")

    if outlook_time and outlook_area:
        outlook_coords = outlook_area.group(1).strip().replace("\n", " ").split("-")
        print(f"\nOutlook Forecast Time: {outlook_time.group(1)} UTC to {outlook_time.group(2)} UTC")
        print("Forecast Area:")
        for point in outlook_coords:
            print(f" - {point.strip()}")

    print("\nAdditional SIGMETs may be issued. Refer to SPC for updates.")

def parse_metar(raw):
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
    print("\nDecoded METAR Report:\n")
    for key, value in result.items():
        final += key
        final += ' '
        final += value
        final += "\n" 
        # print(f"{key}: {value}")
    return final
    
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
        wind_desc = f"Wind from {direction}° at {speed} knots"
        if gust:
            wind_desc += f" with gusts to {gust[1:]} knots"
        return wind_desc
    return None

def parse_taf(taf_str):
    words = taf_str.split()
    translation = []
    
    for word in words:
        if word in taf_dict:
            translation.append(taf_dict[word])
        elif word.startswith("FM"):
            time = word[2:]
            translation.append(f"From {time[:2]}:{time[2:]}Z")
        elif decode_wind(word):
            translation.append(decode_wind(word))
        elif re.match(r"\d{4}/\d{4}", word):  # validity period
            start, end = word[:4], word[5:]
            translation.append(f"Valid from {start[:2]}Z on day {start[2:]} to {end[:2]}Z on day {end[2:]}")
        elif re.match(r"\d{6}Z", word):  # issuance time
            translation.append(f"Issued at {word[:2]} day, {word[2:4]}:{word[4:6]}Z")
        else:
            translation.append(word)

    return "\n".join(translation)


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
def fetch_metar(airport_ids):
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
    response = requests.get(url)
    response = response.json()
    n = len(airport_ids)
    metar_taf = {}
    if n == 0:
        print(response)
        return parse_metar(response[0]['rawOb'])
    for x in range(n):
        airport_data = response[x]
        print(airport_data)
        metar_taf[airport_data['icaoId']] = {
            # 'taf': parse_taf(airport_data['rawTaf']),
            'metar': parse_metar(airport_data['rawOb'])
        }        
    return metar_taf

def fetch_taf(airport_id):
    url = f"https://aviationweather.gov/api/data/taf?ids={airport_id}&format=json"
    response = requests.get(url)
    parse_taf()
    return response.json()

def fetch_pirep(airport_id):
    url = f"https://aviationweather.gov/api/data/pirep?ids={airport_id}&format=json"
    response1 = requests.get(url)
    response1=response1.json()
    return response1

def fetch_sigmet(altitude=None):
    base_url = "https://aviationweather.gov/api/data/airsigmet"
    params = {
        "format": "json"
    }

    response = requests.get(base_url, params=params, timeout=10)
    print(response.json()[0]['rawAirSigmet'])
    response.json()



    
    

# print(parse_metar("KPHX 210151Z 31006KT 10SM SCT250 28/01 A2990 RMK AO2 SLP113 T02830011"))
# print(parse_taf("KPHX 202328Z 2100/2206 27006KT P6SM FEW250 FM210700 10005KT P6SM SCT250 FM211900 28007KT P6SM BKN250"))
# rawAirSigmet = "WSUS31 KKCI 210155 \nSIGE  \nCONVECTIVE SIGMET...NONE \n \nOUTLOOK VALID 210355-210755 \nFROM 70NE GRB-30E TVC-30SSE DXO-60E CVG-60SSE TTH-70NE GRB \nWST ISSUANCES POSS LT IN PD. REFER TO MOST RECENT ACUS01 KWNS \nFROM STORM PREDICTION CENTER FOR SYNOPSIS AND METEOROLOGICAL \nDETAILS."
# parse_sigmet(rawAirSigmet)
# parse_sigmet("WSUS32 KKCI 210155 \nSIGC  \nCONVECTIVE SIGMET 3C \nVALID UNTIL 0355Z \nWI IL MO AR IA \nFROM 40ENE DBQ-40NW TTH-40N MEM-50SW ARG-STL-50W DBQ-40ENE DBQ \nAREA SEV EMBD TS MOV FROM 24050KT. TOPS ABV FL450. \nTORNADOES...HAIL TO 1.5 IN...WIND GUSTS TO 60KT POSS. \n \nOUTLOOK VALID 210355-210755 \nFROM 70NE GRB-60SSE TTH-30ENE MCB-70ESE PSX-40NNE CRP-30NNW \nELD-30SSE STL-40NW ODI-70NE GRB \nREF WW 155 156. \nWST ISSUANCES EXPD. REFER TO MOST RECENT ACUS01 KWNS FROM STORM \nPREDICTION CENTER FOR SYNOPSIS AND METEOROLOGICAL DETAILS.")
# parse_sigmet("WSUS32 KKCI 210155 \nSIGC  \nCONVECTIVE SIGMET 4C \nVALID UNTIL 0355Z \nLA AR TX \nFROM 30NNW MEM-40ESE IAH-50NNW PSX-60NNE LIT-30NNW MEM \nAREA SEV EMBD TS MOV FROM 22040KT. TOPS ABV FL450. \nHAIL TO 1.5 IN...WIND GUSTS TO 60KT POSS. \n \nOUTLOOK VALID 210355-210755 \nFROM 70NE GRB-60SSE TTH-30ENE MCB-70ESE PSX-40NNE CRP-30NNW \nELD-30SSE STL-40NW ODI-70NE GRB \nREF WW 155 156. \nWST ISSUANCES EXPD. REFER TO MOST RECENT ACUS01 KWNS FROM STORM \nPREDICTION CENTER FOR SYNOPSIS AND METEOROLOGICAL DETAILS.")
# parse_sigmet("WSUS33 KKCI 210155 \nSIGW  \nCONVECTIVE SIGMET 3W \nVALID UNTIL 0355Z \nMT \nFROM 60WNW HVR-50NE GGW-50ENE MLS-40S LWT-60WNW HVR \nAREA EMBD TS MOV FROM 27015KT. TOPS TO FL260. \n \nOUTLOOK VALID 210355-210755 \nTS ARE NOT EXPD TO REQUIRE WST ISSUANCES.")
# api = "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"
