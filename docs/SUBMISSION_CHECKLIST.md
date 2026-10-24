# Congressional App Challenge submission checklist

Deadline: **Monday, October 26, 2026, 12:00 PM ET.** Aim to submit Sunday.

## Before you submit
- [ ] Test the map with 3 or 4 real Franklin County addresses (a normal street, a corner lot, a condo). Check that
      Left / Right / Behind match what you see on the satellite view.
- [ ] Both team members are eligible: enrolled in middle or high school on October 26, 2026, and at least half the
      team lives or goes to school in Ohio's 3rd district.
- [ ] Every link and phone number in `titlecheck/resources.py` still works (open each one).
- [ ] Recorder fee: check the Franklin County Recorder's fee calculator and decide whether to show the amount.
- [ ] Test with 2 or 3 real people (an older relative or neighbor). Write down what confused them and fix it.
- [ ] Your own changes are committed to GitHub under your own names.
- [ ] The app is live on Vercel and the link is in the README.
- [ ] "Team" and "Use of AI tools" are filled in, in the README and on the About page (`app_pages/about.py`).

## Demo video (1 to 3 minutes, public on YouTube or Vimeo)
The rules require all of these:
- [ ] Each team member's name
- [ ] App name
- [ ] Purpose in one clear sentence
- [ ] Target audience
- [ ] Tools and coding languages used (Python, Flask, HTML / CSS / JavaScript, requests, fpdf2, folium / Leaflet,
      pytest, Vercel, Franklin County ArcGIS REST data)
- [ ] A live demo of the app working

Suggested order: why you care (15 s), the problem with one number (15 s), live demo (90 s): the demo home, the
property map (switch to satellite, point out Left / Right / Behind, click a neighbor, measure the lot with the ruler),
the questions and the result, then "Who would inherit?" (add a child who died with 2 children, then drag the
generations slider), privacy and safety choices (15 s), what's next (15 s). Explain one thing you understand deeply,
like how the app decides which neighbor is on the left.

## Written questions (answer in your own words)
1. App title
2. Purpose
3. Inspiration: what made you care about inherited homes?
4. Technical difficulties and how you solved them. Real examples from this project: the County's address format
   (abbreviations, ZIP codes), owner-occupancy fields that turned out to be empty, dollar signs being read as math
   formatting, keeping the lookup safe from malicious input.
5. What you learned and your biggest takeaway
6. What you'd change in a 2.0 version (see the README for ideas)

## AI disclosure
Say clearly which parts were AI-generated and which parts you built, changed and tested yourselves. The rules allow
AI tools only if all use is fully disclosed, and they require significant individual contribution and real
understanding of the app.
