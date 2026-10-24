import streamlit as st
from streamlit_folium import st_folium

from titlecheck.assess import display_name as pretty
from titlecheck.geo import FT_PER_M, analyze, center_lonlat, point_in_rings
from titlecheck.lookup import AddressLookupError, Parcel, find_in_view, find_nearby, find_parcels, parcel_at
from titlecheck.parcel_map import LINES_FROM_ZOOM, START, explore_map, lots_layer

# this page needs room: let the map use the whole width
st.markdown("<style>.block-container {max-width: 1400px;}</style>", unsafe_allow_html=True)


@st.cache_data(ttl=600, show_spinner=False)
def lots_in_view(box: tuple[float, float, float, float]) -> list[Parcel]:
    return find_in_view(box)


@st.cache_data(ttl=600, show_spinner=False)
def lots_around(_home: Parcel, parcel_id: str) -> list[Parcel]:
    return find_nearby(_home)


def view_box(state: dict) -> tuple[float, float, float, float] | None:
    """The part of the map on screen, rounded so small moves reuse the County's last answer."""
    b = (state or {}).get("bounds") or {}
    sw, ne = b.get("_southWest"), b.get("_northEast")
    if not sw or not ne or sw.get("lat") is None:
        return None
    return tuple(round(v, 4) for v in (sw["lng"], sw["lat"], ne["lng"], ne["lat"]))


st.title("Property map")
st.markdown("Explore any neighborhood in Franklin County on a real satellite map. Zoom in and the County's property "
            "lines appear. **Click a home** to see its lot and who lives on the left, right and behind.")

with st.form("find_on_map"):
    c1, c2 = st.columns([4, 1])
    typed = c1.text_input("Go to an address", placeholder="123 Main St, Columbus, OH 43215",
                          label_visibility="collapsed")
    go = c2.form_submit_button("Go", type="primary", icon=":material/search:", width="stretch")
if go and typed:
    try:
        found = find_parcels(typed)
    except AddressLookupError as e:
        st.error(str(e))
        found = None
    if found == []:
        st.warning("No Franklin County property matched that address. Check the spelling and try again.")
    elif found and found[0].rings:
        st.session_state.ex_selected = found[0]
        lon, lat = center_lonlat(found[0].rings)
        st.session_state.ex_center, st.session_state.ex_zoom = (lat, lon), 19

center = st.session_state.setdefault("ex_center", START)
zoom = st.session_state.setdefault("ex_zoom", 17)
state = st.session_state.get("explore_map") or {}
selected: Parcel | None = st.session_state.get("ex_selected")

# ------------------------------------------------------------------ property lines for what's on screen
lots: list[Parcel] = []
box = view_box(state)
current_zoom = state.get("zoom") or zoom
problem = None
if box is not None and current_zoom >= LINES_FROM_ZOOM:
    try:
        lots = lots_in_view(box)
    except AddressLookupError as e:
        problem = str(e)

shape, neighbors = None, []
if selected is not None:
    try:
        around = lots_around(selected, selected.parcel_id)
    except AddressLookupError:
        around = [p for p in lots if p.parcel_id != selected.parcel_id]
    shape, neighbors = analyze(selected.rings, {p.parcel_id: p.rings for p in around})
    known = {p.parcel_id for p in lots}
    lots = lots + [p for p in around if p.parcel_id not in known]

# ------------------------------------------------------------------ the map
left, right = st.columns([2.3, 1], gap="medium")
with left:
    out = st_folium(explore_map(center, zoom), key="explore_map", height=640, use_container_width=True,
                    center=center, zoom=zoom, feature_group_to_add=lots_layer(lots, selected, neighbors, shape),
                    returned_objects=["bounds", "zoom", "last_clicked"])
    if problem:
        st.warning(problem)
    elif current_zoom < LINES_FROM_ZOOM:
        st.info("Zoom in closer to see property lines.", icon=":material/zoom_in:")
    st.caption("Switch between the satellite photo and the street map (buildings and landmarks) with the layers "
               "button in the top-right corner. The ruler measures distances and areas.")

# a click on the map picks the lot under it
click = (out or {}).get("last_clicked")
if click and click != st.session_state.get("ex_last_click"):
    st.session_state.ex_last_click = click
    point = (click["lng"], click["lat"])
    hit = next((p for p in lots if point_in_rings(point, p.rings)), None)
    if hit is None:
        try:
            hit = parcel_at(*point)
        except AddressLookupError:
            hit = None
    if hit is not None and (selected is None or hit.parcel_id != selected.parcel_id):
        st.session_state.ex_selected = hit
        lon, lat = center_lonlat(hit.rings)      # zoom in on it so the neighbor labels have room
        st.session_state.ex_center, st.session_state.ex_zoom = (lat, lon), max(19, state.get("zoom") or 19)
        st.rerun()

# ------------------------------------------------------------------ the chosen lot
with right:
    if selected is None:
        st.subheader("Click a home")
        st.markdown("Pick any lot on the map, or type an address above.\n\n"
                    "- **Blue**: the home you picked\n- **Orange**: the lots that touch it, marked **L**, **R** and "
                    "**B** (left, right and behind, as seen from the street)\n- **Purple (A)**: across the street\n"
                    "- **Yellow**: every other property line")
    else:
        st.subheader(selected.address or "Lot with no street address")
        owners = ", ".join(pretty(o) for o in selected.owners) or "No owner listed"
        st.markdown(f"**Owner(s):** {owners}")
        if shape is not None:
            st.markdown(f"**Lot size:** {shape.acres:.2f} acres ({shape.area_sq_ft:,.0f} sq ft)")
            if shape.frontage_ft:
                st.markdown(f"**Along the street:** about {shape.frontage_ft:,.0f} ft")
        if selected.property_class:
            st.markdown(f"**Type:** {selected.property_class.capitalize()}")
        st.markdown(f"[See it on the Auditor's website]({selected.auditor_link})")
        by_id = {p.parcel_id: p for p in lots}
        if neighbors:
            st.markdown("**Neighbors**")
            for n in neighbors:
                p = by_id.get(n.key)
                if p is not None:
                    line = f" (shares {n.shared_m * FT_PER_M:,.0f} ft)" if n.shared_m else ""
                    st.markdown(f"- **{n.position}:** {p.address or 'no street address'}{line}")
        if st.button("Check this home's title", type="primary", icon=":material/fact_check:", width="stretch"):
            for k in list(st.session_state):
                if k.startswith(("q_", "alive_")) or k in ("matches", "manual"):
                    del st.session_state[k]
            st.session_state.parcel = selected
            st.switch_page("app_pages/check.py")
        if st.button("Clear", icon=":material/close:", width="stretch"):
            del st.session_state["ex_selected"]
            st.rerun()
    st.caption("Shows only what the County's public map shows. This map never shows a title status for any home.")
