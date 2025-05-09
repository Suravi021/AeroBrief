# ✈️ AI Powered Weather Summaries for Flight Plans


The **Aero Brief** is an interactive application built with Streamlit that allows pilots and flight planners to input airports, retrieve METAR and TAF reports, visualize the flight path on a map, and identify significant weather phenomena such as PIREPs and SIGMETs.

---


![Flight Weather Map](.images/map.png)

---

## 🔧 Features

- Dynamically add/remove airport waypoints
- View METAR and TAF reports for each airport
- Color-coded weather warnings based on severity (VFR, MVFR, IFR, LIFR, UNKNOWN)
- Leaflet.js map visualization of:
  - Airport locations
  - Flight route (with curved lines for low altitude legs)
  - PIREPs and SIGMET areas
  - Weather warnings near the route
- Summary report with flight condition overview

---

## 🚀 Installation

1. **Clone this repository**

```bash
git clone https://github.com/your-username/AeroBrief.git
cd AeroBrief
