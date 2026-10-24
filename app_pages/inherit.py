import altair as alt
import pandas as pd
import streamlit as st

from titlecheck.heirs import Child, Family, generations, who_inherits
from titlecheck.resources import link

st.title("Who would inherit the home?")
st.markdown("When an Ohio homeowner dies **without a will and without a Transfer on Death affidavit**, state law "
            "decides who owns the home next. Build the family below to see how the home would be split, and how "
            "many people would have to sign to sell it, refinance it, or fix the title.")
st.caption("A simplified version of Ohio's rules (ORC 2105.06). A will, debts, or a more complicated family change "
           "the answer. General information, not legal advice. Nothing you type is saved.")

# ------------------------------------------------------------------ build the family
st.header("1. The family")
spouse = st.toggle("The owner's husband or wife is living", key="h_spouse")
count = st.number_input("How many children did the owner have?", 0, 10, 2, key="h_count")
children = []
for i in range(int(count)):
    c1, c2, c3 = st.columns([2, 1.3, 1.7])
    name = c1.text_input(f"Child {i + 1}", value=f"Child {i + 1}", key=f"h_name_{i}").strip() or f"Child {i + 1}"
    living = c2.toggle("Living", value=True, key=f"h_living_{i}")
    grandkids = 0
    if not living:
        grandkids = c3.number_input("Their children", 0, 10, 0, key=f"h_gk_{i}")
    with_spouse = True
    if spouse:
        with_spouse = c3.checkbox("Also the spouse's child", value=True, key=f"h_ws_{i}")
    children.append(Child(name, living, int(grandkids), with_spouse))

parents = siblings = 0
if not any(c.living or c.grandchildren for c in children) and not spouse:
    c1, c2 = st.columns(2)
    parents = c1.number_input("Parents living", 0, 2, 0, key="h_parents")
    siblings = c2.number_input("Brothers and sisters living", 0, 15, 0, key="h_sibs")

result = who_inherits(Family(spouse, children, int(parents), int(siblings)))

# ------------------------------------------------------------------ the result
st.header("2. Who owns the home")
if not result.heirs:
    st.warning(result.explanation)
else:
    n = result.signers
    st.markdown(f"<div class='status-box status-{'green' if n == 1 else 'orange' if n <= 3 else 'red'}'>"
                f"<h3>{n} {'person owns' if n == 1 else 'people would own'} the home</h3>"
                f"{'One person can handle the title.' if n == 1 else f'All {n} would have to agree and sign to sell or refinance it.'}"
                f"</div>", unsafe_allow_html=True)
    st.markdown(result.explanation.replace("$", "\\$") + f" ({result.law})")
    df = pd.DataFrame({"Heir": [h.name for h in result.heirs],
                       "Share": [float(h.share) for h in result.heirs],
                       "Fraction": [str(h.share) for h in result.heirs]})
    df["Percent"] = (df["Share"] * 100).round(1).astype(str) + "%"
    donut = alt.Chart(df).mark_arc(innerRadius=70, stroke="#fff").encode(
        theta="Share:Q", color=alt.Color("Heir:N", legend=alt.Legend(orient="bottom", columns=2)),
        tooltip=["Heir", "Fraction", "Percent"]).properties(height=320)
    st.altair_chart(donut, width="stretch")
    if result.spouse_first_amount:
        st.caption(f"The spouse's \\${result.spouse_first_amount:,} comes off the top of the whole estate first, "
                   "so the real split of the home depends on what else was left. Ask Legal Aid.")
    st.dataframe(df[["Heir", "Fraction", "Percent"]], hide_index=True)

# ------------------------------------------------------------------ generations
st.header("3. What happens if nobody files for generations")
st.markdown("Every time an owner dies without the paperwork, their share splits again among their heirs. "
            "Drag the sliders to watch it happen.")
c1, c2 = st.columns(2)
kids = c1.slider("Children per person", 1, 5, 3)
gens = c2.slider("Generations", 1, 5, 3)
rows = generations(kids, gens)
gdf = pd.DataFrame({"Generation": [f"{'Original owner' if g == 0 else f'Generation {g}'}" for g, _ in rows],
                    "Owners": [o for _, o in rows], "Order": [g for g, _ in rows]})
bars = alt.Chart(gdf).mark_bar(color="#c5221f").encode(
    x=alt.X("Generation:N", sort=alt.SortField("Order"), title=None, axis=alt.Axis(labelAngle=0)),
    y=alt.Y("Owners:Q", title="People who own a piece of the home"), tooltip=["Generation", "Owners"])
st.altair_chart(bars, width="stretch")
last = rows[-1][1]
st.markdown(f"After **{gens}** generation{'s' if gens > 1 else ''}, **{last:,} people** each own about "
            f"**{100 / last:.2f}%** of the home. Every one of them has to be found and has to sign before the home "
            "can be sold, refinanced or repaired with a loan.")

st.info("The fix takes one form, recorded while the owner is alive: a Transfer on Death Designation Affidavit "
        f"({link('tod_forms')}). Then the home goes straight to the people named, with no court.",
        icon=":material/lightbulb:")
st.page_link("app_pages/check.py", label="Check a home now", icon=":material/arrow_forward:")
