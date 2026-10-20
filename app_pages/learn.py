import streamlit as st

from titlecheck.resources import FACTS, link

st.title("What is a tangled title?")
st.markdown("""
**"Grandma's house is still in Grandpa's name."**

When someone who owns a home dies, the home doesn't move to the family on its own. Someone has to file paperwork
with the County or go through probate court. If nobody does, the family keeps living there, but legally the home
still belongs to the person who died. That's called a **tangled title** (or *heirs' property*).

With every generation it gets harder to fix, because the ownership splits among more and more relatives:
""")

st.graphviz_chart("""
digraph G {
  rankdir=LR; node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=12];
  g [label="Grandpa\\n(name on the deed)\\n1 owner", fillcolor="#e8f0fe"];
  k1 [label="4 children\\neach owns 1/4", fillcolor="#fff4e5"];
  k2 [label="2 living children\\n+ 9 grandchildren\\neach owns a small share", fillcolor="#fdecea"];
  g -> k1 [label="dies, nothing filed"]; k1 -> k2 [label="2 of them die"];
}
""")

st.markdown((f"""
### What it costs a family
- {FACTS['blocked']}
- Selling or refinancing usually needs every heir to agree and sign, and some heirs may be hard to find.
- Unpaid property taxes can still lead to foreclosure while the title is tangled.

### How big is it?
- {FACTS['ohio_count']}
- {FACTS['ohio_value']}
- Experts think it's concentrated in neighborhoods that faced long-term disinvestment, where families had less
  access to lawyers and estate planning.

### The easy fix most people don't know about
Ohio has a **Transfer on Death Designation Affidavit**: a short form the owner signs in front of a notary and records
with the County Recorder. When the owner dies, the home goes straight to the people named, with no probate.
It has to be recorded **while the owner is alive**. Forms: {link('tod_forms')}.

If the owner has already died, the family usually needs probate court. Small estates can use a shorter process.
**Check your home** to see which steps fit your family.
""").replace("$", "\\$"))
st.page_link("app_pages/check.py", label="Check my home", icon=":material/arrow_forward:")
