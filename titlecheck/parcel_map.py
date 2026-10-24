"""The interactive property map: the home's lot, its neighbors, and every property line around it (Leaflet, via folium).

Privacy: neighbors show only what the County shows on its own public map (address, owner, lot size). No neighbor ever
gets a title status, a last-sale date or any other hint about their family, so the map can't be used to hunt for
tangled titles.
"""
from __future__ import annotations

import folium
from folium.plugins import Fullscreen, MeasureControl

from titlecheck.geo import LotShape, Neighbor, center_lonlat
from titlecheck.lookup import Parcel

HOME_COLOR = "#1a73e8"
NEIGHBOR_COLOR = "#e37400"
ACROSS_COLOR = "#9334e6"
LINE_COLOR = "#5f6368"          # other property lines on the plain demo background
IMAGERY_LINE_COLOR = "#ffffff"  # ...and on the satellite photo, where gray disappears
BADGE = {"Left": "L", "Right": "R", "Behind": "B", "Next door": "N", "Across the street": "A"}

SATELLITE = ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}")
SATELLITE_CREDIT = "Imagery &copy; Esri, Maxar, Earthstar Geographics, and the GIS User Community"
STREET_NAMES = ("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/"
                "{z}/{y}/{x}")
STREET_NAMES_CREDIT = "Streets &copy; Esri"


def _feature(p: Parcel, role: str, label: str) -> dict:
    # GeoJSON wants [lon, lat] lists; the County rings are already (lon, lat)
    return {"type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[list(pt) for pt in ring] for ring in p.rings]},
            "properties": {"parcel_id": p.parcel_id, "address": p.address or "No street address", "role": role,
                           "label": label}}


def _style(role: str, imagery: bool):
    # on the satellite photo: lighter fills so the roofs and yards show through, thicker lines so they stand out
    color, weight, fill = {"home": (HOME_COLOR, 4, 0.35), "neighbor": (NEIGHBOR_COLOR, 3, 0.18),
                           "across": (ACROSS_COLOR, 2, 0.12)}.get(role, (LINE_COLOR, 1, 0.03))
    if imagery:
        weight, fill = weight + 1, fill / 2
        if role == "other":
            color, weight = IMAGERY_LINE_COLOR, 1.5
    return lambda _: {"color": color, "weight": weight, "fillColor": color, "fillOpacity": fill}


def _badge(text: str, color: str) -> folium.DivIcon:
    return folium.DivIcon(icon_size=(30, 30), icon_anchor=(15, 15),
                          html=f"<div style='background:{color};color:#fff;border-radius:50%;width:30px;height:30px;"
                               f"display:flex;align-items:center;justify-content:center;font:bold 14px sans-serif;"
                               f"box-shadow:0 1px 4px rgba(0,0,0,.4)'>{text}</div>")


def build_map(home: Parcel, nearby: list[Parcel], neighbors: list[Neighbor], shape: LotShape | None,
              demo: bool = False) -> folium.Map:
    lon, lat = center_lonlat(home.rings)
    m = folium.Map(location=[lat, lon], zoom_start=19, max_zoom=22, tiles=None, control_scale=True)
    if demo:
        # made-up block: plain background, no real street or rooftop under it
        m.get_root().header.add_child(folium.Element("<style>.leaflet-container{background:#eef3ea}</style>"))
    else:
        # satellite photo underneath the property lines; the street map waits in the layer menu (show=False)
        folium.TileLayer(SATELLITE, attr=SATELLITE_CREDIT, name="Satellite", max_zoom=22,
                         max_native_zoom=19).add_to(m)
        folium.TileLayer("OpenStreetMap", name="Street map", max_zoom=22, max_native_zoom=19, show=False).add_to(m)
        folium.TileLayer(STREET_NAMES, attr=STREET_NAMES_CREDIT, name="Street names", overlay=True, show=True,
                         max_zoom=22, max_native_zoom=19).add_to(m)
    imagery = not demo

    place = {n.key: n for n in neighbors}
    lines = folium.FeatureGroup(name="Property lines", show=True)
    for p in nearby:
        n = place.get(p.parcel_id)
        if n is None:
            role, label = "other", "Nearby lot"
        else:
            role = "across" if n.position == "Across the street" else "neighbor"
            label = n.position if n.position in ("Across the street", "Next door") else f"Neighbor: {n.position}"
        folium.GeoJson(_feature(p, role, label), style_function=_style(role, imagery),
                       highlight_function=lambda _: {"weight": 5, "fillOpacity": 0.4},
                       tooltip=folium.GeoJsonTooltip(["label", "address"], aliases=["", ""])).add_to(lines)
        if n is not None:
            c_lon, c_lat = center_lonlat(p.rings)
            folium.Marker([c_lat, c_lon], icon=_badge(BADGE[n.position], ACROSS_COLOR if role == "across"
                                                     else NEIGHBOR_COLOR),
                          tooltip=f"{label}: {p.address}").add_to(lines)
    lines.add_to(m)

    home_label = "This home"
    if shape is not None:
        home_label += f" ({shape.acres:.2f} acres)"
    folium.GeoJson(_feature(home, "home", home_label), style_function=_style("home", imagery),
                   tooltip=folium.GeoJsonTooltip(["label", "address"], aliases=["", ""]), name="This home").add_to(m)
    folium.Marker([lat, lon], icon=_badge("&#8962;", HOME_COLOR), tooltip=home_label).add_to(m)

    Fullscreen(position="topleft").add_to(m)
    MeasureControl(position="topleft", primary_length_unit="feet", secondary_length_unit="meters",
                   primary_area_unit="sqfeet", secondary_area_unit="acres").add_to(m)
    if not demo:
        folium.LayerControl(collapsed=False).add_to(m)
    m.fit_bounds([[min(y for r in home.rings for _, y in r), min(x for r in home.rings for x, _ in r)],
                  [max(y for r in home.rings for _, y in r), max(x for r in home.rings for x, _ in r)]],
                 padding=(120, 120))
    return m
