"""The interactive property maps (Leaflet, via folium): real satellite photos and street maps, with the County's
property lines drawn on top.

Privacy: neighbors show only what the County shows on its own public map (address, owner, lot size). No lot ever
gets a title status, a last-sale date or any other hint about the family, so the maps can't be used to hunt for
tangled titles.
"""
from __future__ import annotations

import folium
from folium.plugins import Fullscreen, LocateControl, MeasureControl

from titlecheck.geo import LotShape, Neighbor, center_lonlat
from titlecheck.lookup import Parcel

HOME_COLOR = "#1a73e8"
NEIGHBOR_COLOR = "#e37400"
ACROSS_COLOR = "#9334e6"
LINE_COLOR = "#5f6368"          # other property lines on the plain demo background
VIEW_LINE_COLOR = "#ffd54f"     # other property lines on real maps: a yellow that shows on photos and street maps
BADGE = {"Left": "L", "Right": "R", "Behind": "B", "Next door": "N", "Across the street": "A"}

ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/{}/MapServer/tile/{{z}}/{{y}}/{{x}}"
SATELLITE_CREDIT = "Imagery &copy; Esri, Maxar, Earthstar Geographics, and the GIS User Community"

# where the Property map opens: the Ohio Statehouse, downtown Columbus (a public building, not anyone's home)
START = (39.9612, -82.9988)
LINES_FROM_ZOOM = 17            # property lines appear from this zoom in (closer than that there are too many)


def add_base_layers(m: folium.Map) -> None:
    """Satellite photo (default) and street map, with street and place names on top of the photo."""
    folium.TileLayer(ESRI.format("World_Imagery"), attr=SATELLITE_CREDIT, name="Satellite", max_zoom=22,
                     max_native_zoom=19).add_to(m)
    folium.TileLayer("OpenStreetMap", name="Street map (buildings, landmarks)", max_zoom=22, max_native_zoom=19,
                     show=False).add_to(m)
    folium.TileLayer(ESRI.format("Reference/World_Transportation"), attr="Streets &copy; Esri", name="Street names",
                     overlay=True, max_zoom=22, max_native_zoom=19).add_to(m)
    folium.TileLayer(ESRI.format("Reference/World_Boundaries_and_Places"), attr="Places &copy; Esri",
                     name="Place names and landmarks", overlay=True, max_zoom=22, max_native_zoom=19).add_to(m)


def add_tools(m: folium.Map) -> None:
    Fullscreen(position="topleft").add_to(m)
    MeasureControl(position="topleft", primary_length_unit="feet", secondary_length_unit="meters",
                   primary_area_unit="sqfeet", secondary_area_unit="acres").add_to(m)


def _feature(p: Parcel, role: str, label: str) -> dict:
    # GeoJSON wants [lon, lat] lists; the County rings are already (lon, lat)
    return {"type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[list(pt) for pt in ring] for ring in p.rings]},
            "properties": {"parcel_id": p.parcel_id, "address": p.address or "No street address", "role": role,
                           "label": label}}


STYLES = {  # role -> (line color, line width, fill opacity)
    "home": (HOME_COLOR, 4, 0.25), "neighbor": (NEIGHBOR_COLOR, 3, 0.12), "across": (ACROSS_COLOR, 2.5, 0.08),
    "other": (VIEW_LINE_COLOR, 1.5, 0.02), "demo-other": (LINE_COLOR, 1, 0.03),
}


def _style(feature: dict) -> dict:
    color, weight, fill = STYLES[feature["properties"]["role"]]
    return {"color": color, "weight": weight, "fillColor": color, "fillOpacity": fill}


def _badge(text: str, color: str) -> folium.DivIcon:
    return folium.DivIcon(icon_size=(30, 30), icon_anchor=(15, 15),
                          html=f"<div style='background:{color};color:#fff;border-radius:50%;width:30px;height:30px;"
                               f"display:flex;align-items:center;justify-content:center;font:bold 14px sans-serif;"
                               f"box-shadow:0 1px 4px rgba(0,0,0,.4)'>{text}</div>")


def lots_layer(lots: list[Parcel], home: Parcel | None, neighbors: list[Neighbor], shape: LotShape | None,
               demo: bool = False) -> folium.FeatureGroup:
    """All the property lines, with the chosen home in blue and its neighbors labeled."""
    group = folium.FeatureGroup(name="Property lines")
    place = {n.key: n for n in neighbors}
    features = []
    for p in lots:
        if home is not None and p.parcel_id == home.parcel_id:
            continue
        n = place.get(p.parcel_id)
        if n is None:
            role, label = ("demo-other" if demo else "other"), "Lot"
        else:
            role = "across" if n.position == "Across the street" else "neighbor"
            label = n.position if n.position in ("Across the street", "Next door") else f"Neighbor: {n.position}"
        features.append(_feature(p, role, label))
    if home is not None:
        label = "This home" + (f" ({shape.acres:.2f} acres)" if shape is not None else "")
        features.append(_feature(home, "home", label))
    if features:
        folium.GeoJson({"type": "FeatureCollection", "features": features}, style_function=_style,
                       highlight_function=lambda _: {"weight": 5, "fillOpacity": 0.3},
                       tooltip=folium.GeoJsonTooltip(["label", "address"], aliases=["", ""])).add_to(group)
    by_id = {p.parcel_id: p for p in lots}
    for n in neighbors:
        if n.key in by_id:
            lon, lat = center_lonlat(by_id[n.key].rings)
            color = ACROSS_COLOR if n.position == "Across the street" else NEIGHBOR_COLOR
            folium.Marker([lat, lon], icon=_badge(BADGE[n.position], color),
                          tooltip=f"{n.position}: {by_id[n.key].address}").add_to(group)
    if home is not None:
        lon, lat = center_lonlat(home.rings)
        folium.Marker([lat, lon], icon=_badge("&#8962;", HOME_COLOR), tooltip="This home").add_to(group)
    return group


def explore_map(center: tuple[float, float], zoom: int) -> folium.Map:
    """The full Property map: real map layers only. The property lines are added (and swapped as you move around)
    by the page, so the map itself doesn't reload."""
    m = folium.Map(location=list(center), zoom_start=zoom, max_zoom=22, tiles=None, control_scale=True)
    add_base_layers(m)
    add_tools(m)
    LocateControl(position="topleft", strings={"title": "Show where I am"}).add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    return m


def build_map(home: Parcel, nearby: list[Parcel], neighbors: list[Neighbor], shape: LotShape | None,
              demo: bool = False) -> folium.Map:
    """The small map on the checkup page: one home and its block."""
    lon, lat = center_lonlat(home.rings)
    m = folium.Map(location=[lat, lon], zoom_start=19, max_zoom=22, tiles=None, control_scale=True)
    if demo:
        # made-up block: plain background, no real street or rooftop under it
        m.get_root().header.add_child(folium.Element("<style>.leaflet-container{background:#eef3ea}</style>"))
    else:
        add_base_layers(m)
    lots_layer(nearby, home, neighbors, shape, demo).add_to(m)
    add_tools(m)
    if not demo:
        folium.LayerControl(collapsed=True).add_to(m)
    m.fit_bounds([[min(y for r in home.rings for _, y in r), min(x for r in home.rings for x, _ in r)],
                  [max(y for r in home.rings for _, y in r), max(x for r in home.rings for x, _ in r)]],
                 padding=(120, 120))
    return m
