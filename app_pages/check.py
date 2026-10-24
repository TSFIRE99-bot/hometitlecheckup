import streamlit as st
from streamlit_folium import st_folium

from titlecheck.assess import (ESTATE_SIZES, NO, UNSURE, YES, Answers, assess, owner_kind, record_notes,
                               why_it_matters)
from titlecheck.checklist import build_pdf
from titlecheck.demo import DEMO, DEMO_NEIGHBORS
from titlecheck.geo import FT_PER_M, SQ_FT_PER_ACRE, analyze, lot_sq_ft
from titlecheck.lookup import AddressLookupError, Parcel, find_nearby, find_parcels
from titlecheck.parcel_map import build_map
from titlecheck.resources import link

CHOICES = [YES, NO, UNSURE]


def pretty(name: str) -> str:
    """County style 'PARKER JAMES L' -> 'James L Parker' (people only)."""
    if owner_kind(name) != "person":
        return name.title()
    parts = name.title().split()
    return " ".join(parts[1:] + parts[:1]) if len(parts) > 1 else name.title()


def md(text: str) -> str:
    """Show dollar signs as dollar signs (Streamlit treats $...$ as math)."""
    return text.replace("$", "\\$")


def ask(label: str, key: str, help_text: str | None = None) -> str:
    return st.radio(label, CHOICES, index=None, horizontal=True, key=key, help=help_text) or UNSURE


def lot_acres(p: Parcel) -> str:
    if not p.rings:
        return "unknown"
    sq_ft = lot_sq_ft(p.rings)
    return f"{sq_ft / SQ_FT_PER_ACRE:.2f} acres ({sq_ft:,.0f} sq ft)"


def get_nearby(p: Parcel) -> list[Parcel] | None:
    """Lots around the home, fetched once per home. None if the County's map service didn't answer."""
    if p.parcel_id == "DEMO":
        return DEMO_NEIGHBORS
    cache = st.session_state.setdefault("nearby", {})
    if p.parcel_id not in cache:
        try:
            cache[p.parcel_id] = find_nearby(p)
        except AddressLookupError:
            return None
    return cache[p.parcel_id]


def reset():
    for k in list(st.session_state):
        if k.startswith(("q_", "alive_")) or k in ("parcel", "matches", "manual", "nearby"):
            del st.session_state[k]


st.title("Home Title Checkup")
st.markdown("**Is your family's home legally in the right name?** Find out in 2 minutes, and get the free steps "
            "to fix it or protect it. For homes in Franklin County, Ohio.")
st.caption("Nothing you type is saved. General information, not legal advice.")

# ------------------------------------------------------------------ step 1: find the home
st.header("1. Find the home")
with st.form("lookup"):
    address = st.text_input("Street address", placeholder="123 Main St, Columbus, OH 43215")
    c1, c2 = st.columns(2)
    go = c1.form_submit_button("Look it up", type="primary", icon=":material/search:", width="stretch")
    demo = c2.form_submit_button("Try a demo home", icon=":material/play_arrow:", width="stretch")

if demo:
    reset()
    st.session_state.parcel = DEMO
elif go:
    reset()
    with st.spinner("Checking the Franklin County Auditor's public records..."):
        try:
            matches = find_parcels(address)
        except AddressLookupError as e:
            st.error(str(e))
            matches = None
            st.session_state.manual = True
    if matches is not None:
        if not matches:
            st.warning("No Franklin County property matched that address. Check the spelling, or type the owner "
                       f"names yourself below. You can also search the {link('auditor_search')}.")
            st.session_state.manual = True
        elif len(matches) == 1:
            st.session_state.parcel = matches[0]
        else:
            st.session_state.matches = matches

if "matches" in st.session_state and "parcel" not in st.session_state:
    options = {f"{m.address}, {m.zip_code}": m for m in st.session_state.matches}
    pick = st.radio("A few properties matched. Which one?", list(options), index=None)
    if pick:
        st.session_state.parcel = options[pick]
        st.rerun()

if st.session_state.get("manual") and "parcel" not in st.session_state:
    with st.form("manual_entry"):
        st.markdown("**Type the names on the deed** (from the tax bill or the Auditor's website), one per line.")
        names = st.text_area("Owner names", placeholder="Louise Parker\nJames Parker")
        if st.form_submit_button("Continue", type="primary"):
            owners = [n.strip().upper() for n in names.splitlines() if n.strip()]
            if owners:
                # typed names are 'First Last'; store them the County's way ('LAST FIRST') so display matches
                owners = [" ".join(n.split()[-1:] + n.split()[:-1]) for n in owners]
                st.session_state.parcel = Parcel("MANUAL", address or "Entered by hand", "", owners, None, "")
                st.rerun()

parcel: Parcel | None = st.session_state.get("parcel")
if parcel is None:
    st.info("Start by typing an address, or try the demo home to see how it works.", icon=":material/arrow_upward:")
    st.stop()

# ------------------------------------------------------------------ the record
st.markdown("**What the County record says**")
nearby = get_nearby(parcel) if parcel.rings else None
shape, neighbors = analyze(parcel.rings, {p.parcel_id: p.rings for p in nearby or []}) if parcel.rings else (None, [])
owners_txt = "<br>".join(pretty(o) for o in parcel.owners) or "No owner listed"
when = f"{parcel.last_transfer:%Y}" if parcel.last_transfer else "unknown"
lot_txt = ""
if shape is not None:
    lot_txt = f"<br>Lot size: {shape.acres:.2f} acres ({shape.area_sq_ft:,.0f} sq ft)"
    if shape.frontage_ft:
        lot_txt += f", about {shape.frontage_ft:,.0f} ft along the street"
link_html = (f"<br><a href='{parcel.auditor_link}' target='_blank'>See it on the Auditor's website</a>"
             if parcel.parcel_id not in ("DEMO", "MANUAL") else "")
st.markdown(f"<div class='record-card'><b>{parcel.address}</b><br>Owner(s) on the deed:<br>{owners_txt}"
            f"<br>Last changed hands: {when}{lot_txt}{link_html}</div>", unsafe_allow_html=True)
notes = record_notes(parcel.owners, parcel.years_since_transfer)
for n in notes:
    st.markdown(md(f"- {n}"))

# ------------------------------------------------------------------ the map
if parcel.rings:
    with st.expander("Property map: your lot lines and neighbors", expanded=True, icon=":material/map:"):
        if nearby is None:
            st.warning("The County's map service didn't answer, so only your lot is shown. Try again in a minute.")
        by_id = {p.parcel_id: p for p in nearby or []}
        fmap = build_map(parcel, nearby or [], neighbors, shape, demo=parcel.parcel_id == "DEMO")
        st.caption("Blue is this home. Orange lots touch it (L = left, R = right, B = behind, as seen from the "
                   "street). Purple is across the street. Gray lines are the other property lines. Use the ruler "
                   "to measure, and click any lot to see its public record.")
        clicked = st_folium(fmap, height=500, use_container_width=True, key=f"map_{parcel.parcel_id}",
                            returned_objects=["last_active_drawing"])
        pick = ((clicked or {}).get("last_active_drawing") or {}).get("properties") or {}
        chosen = by_id.get(pick.get("parcel_id"))
        if chosen is not None:
            o = ", ".join(pretty(x) for x in chosen.owners) or "No owner listed"
            web = (f" [Auditor's page]({chosen.auditor_link})" if not chosen.parcel_id.startswith("DEMO") else "")
            st.markdown(f"**{pick.get('label')}: {chosen.address}**  \nOwner(s): {o}  \n"
                        f"Lot size: {lot_acres(chosen)}{web}")
        if neighbors:
            st.markdown("**Neighbors**")
            st.dataframe([{"Where": n.position, "Address": by_id[n.key].address,
                           "Owner(s)": ", ".join(pretty(x) for x in by_id[n.key].owners),
                           "Shared property line": f"{n.shared_m * FT_PER_M:,.0f} ft" if n.shared_m else "-"}
                          for n in neighbors], hide_index=True)
            st.caption("Left and right are estimated from the shape of the lots. Neighbors only show what the County "
                       "already shows on its public map; this app never shows a title status for anyone else's home.")
else:
    st.caption("No lot outline for this home, so there's no map. You can still finish the checkup.")

# ------------------------------------------------------------------ step 2: questions
st.header("2. A few questions")
people = [o for o in parcel.owners if owner_kind(o) == "person"]
kinds = {owner_kind(o) for o in parcel.owners}
alive = {p: ask(f"Is **{pretty(p)}** living?", key=f"alive_{i}") for i, p in enumerate(people)}
a = Answers(owners_alive=alive)
someone_died = NO in alive.values() or "estate" in kinds

if people and all(v == YES for v in alive.values()) and "estate" not in kinds:
    a.tod_recorded = ask("Has a **Transfer on Death affidavit** been recorded for this home?", "q_tod",
                         "A one-page form, recorded with the County, that names who gets the home next.")
elif someone_died:
    living = [p for p, v in alive.items() if v == YES]
    if living and len(people) >= 2:
        a.survivorship = ask("Does the deed say **'with right of survivorship'**?", "q_surv",
                             "It means the living owner automatically keeps the home.")
    a.tod_recorded = ask("Before the death, was a **Transfer on Death affidavit** recorded?", "q_tod",
                         "A one-page form, recorded with the County, that names who gets the home next.")
    a.probate_opened = ask("Has a **probate case** been opened in court?", "q_probate")
    if a.tod_recorded != YES and a.probate_opened != YES and a.survivorship != YES:
        st.markdown("These help find the simplest court process:")
        a.spouse_gets_all = ask("Is a **surviving spouse** inheriting everything?", "q_spouse")
        a.estate_size = st.radio("Roughly how much was **everything they left** worth, house included?",
                                 ESTATE_SIZES, index=None, horizontal=True, key="q_size", format_func=md) or UNSURE
        a.only_real_estate = ask("Did they leave **only the house** (no bank accounts, cars, or other property)?",
                                 "q_only")

# ------------------------------------------------------------------ step 3: result
st.header("3. Your result")
result = assess(parcel.owners, a)
st.markdown(f"<div class='status-box status-{result.color}'><h3>{result.label}</h3>{result.headline}</div>",
            unsafe_allow_html=True)
for r in result.reasons:
    st.markdown(md(f"- {r}"))

st.subheader("Your action plan")
for i, step in enumerate(result.steps, 1):
    st.markdown(md(f"**{i}. {step.title}**  \n{step.detail}"))

pdf_details = [f"County parcel ID: {parcel.parcel_id}"] if parcel.parcel_id not in ("DEMO", "MANUAL") else []
if shape is not None:
    pdf_details.append(f"Lot size: {shape.acres:.2f} acres ({shape.area_sq_ft:,.0f} sq ft)")
st.download_button("Download a printable checklist (PDF)", build_pdf(result, parcel.address, notes, pdf_details),
                   file_name="home-title-action-plan.pdf", mime="application/pdf", icon=":material/print:")

with st.expander("Why a clear title matters", icon=":material/lightbulb:"):
    for line in why_it_matters():
        st.markdown(md(f"- {line}"))

st.divider()
st.caption("General information about Ohio law, not legal advice. Laws, forms and fees change; confirm with the "
           "County offices or a lawyer before filing anything.")
if st.button("Start over", icon=":material/restart_alt:"):
    reset()
    st.rerun()
