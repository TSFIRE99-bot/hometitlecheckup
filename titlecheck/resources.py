"""Official links and contacts shown in the app. Check these before each release; offices change them."""

LINKS = {
    "auditor_search": ("Franklin County Auditor property search", "https://property.franklincountyauditor.com/"),
    "recorder_search": ("Franklin County Recorder public records search",
                        "https://www.franklincountyohio.gov/Agency-Directory/Recorder/Real-Estate/Public-Records-Search"),
    "tod_forms": ("Transfer on Death affidavit forms (Franklin County Law Library)",
                  "https://fclawlib.libguides.com/TOD/transferondeathaffidavit"),
    "orc_tod": ("Ohio law: Transfer on Death Designation Affidavit (ORC 5302.22)",
                "https://codes.ohio.gov/ohio-revised-code/section-5302.22"),
    "orc_confirm": ("Ohio law: affidavit to confirm the transfer after death (ORC 5302.222)",
                    "https://codes.ohio.gov/ohio-revised-code/section-5302.222"),
    "probate_small": ("Franklin County Probate Court: Small Estates brochure",
                      "https://Probate.franklincountyohio.gov/PBCT-website/media/Documents/Pamphlets/Small-Estates.pdf"),
    "probate_guide": ("Franklin County Probate Court: Estates Filing Guide",
                      "https://probate.franklincountyohio.gov/PBCT-website/media/Documents/PDF/Estates-Filing-Guide-(4-2025).pdf"),
    "ohio_legal_help_probate": ("Ohio Legal Help: how probate works",
                                "https://www.ohiolegalhelp.org/topic/overview-probate-administration-ohio"),
    "lasco": ("Legal Aid of Southeast and Central Ohio: apply for free help", "https://www.lasco.org/apply"),
    "gopc": ("Greater Ohio Policy Center: Heirs' Properties in Ohio",
             "https://www.greaterohio.org/blog/2024/8/27/heirs-properties-in-ohio"),
    "lisc": ("LISC: heirs' property relief in Ohio",
             "https://lisc.org/our-stories/story/lisc-brings-heirs-property-relief-to-under-resourced-communities-in-cincinnati-and-cleveland"),
    "homestead": ("Franklin County Auditor: Homestead Exemption", "https://auditor.franklincountyohio.gov/Real-Estate/Homestead"),
    "homestead_faq": ("Franklin County Auditor: Homestead FAQ",
                      "https://auditor.franklincountyohio.gov/Real-Estate/Homestead/Homestead-FAQ"),
    "dte_105a": ("Homestead application for seniors, disabled persons and surviving spouses (DTE 105A)",
                 "https://audr-forms.franklincountyohio.gov/243193937779980"),
    "dte_105i": ("Homestead application for disabled veterans (DTE 105I)",
                 "https://audr-forms.franklincountyohio.gov/243296080772966"),
    "owner_occupancy": ("Franklin County Auditor: Owner Occupancy Credit",
                        "https://auditor.franklincountyohio.gov/Real-Estate/Tax-Reduction-Programs/Owner-Occupied-Credit"),
    "dte_105c": ("Owner Occupancy Credit application (DTE 105C)",
                 "https://audr-forms.franklincountyohio.gov/243296119610960"),
}

CONTACTS = {
    "auditor": ("Franklin County Auditor, Homestead section", "373 S. High St., 21st floor, Columbus, OH 43215",
                "(614) 525-3240"),
    "recorder": ("Franklin County Recorder", "373 S. High St., 18th floor, Columbus, OH 43215", "(614) 525-3930"),
    "probate": ("Franklin County Probate Court (procedure questions, not legal advice)", "", "(614) 525-3894"),
    "lasco": ("Legal Aid of Southeast and Central Ohio", "lasco.org/apply", "(614) 221-7201"),
    "lasco_intake": ("Legal Aid intake line", "weekdays 9:30 a.m. to 1:30 p.m.", "(888) 246-4420"),
}

# Franklin County Recorder fee schedule (ORC 317.32), checked October 2026
FEES = {
    "recording": "$34 for the first two pages, plus $8 for each extra page",
    "recording_short": "$34 recording fee (2 pages)",
    "court": "Court filing fees (ask the clerk)",
}

FACTS = {
    "ohio_count": "Ohio has an estimated 9,000 heirs' properties (Greater Ohio Policy Center, 2024).",
    "ohio_value": "Those homes hold about $313 million in family wealth that clear titles could unlock (LISC, 2024).",
    "blocked": ("Without a clear title, families can't get home-repair financing, claim the homestead tax break, "
                "get disaster aid, or borrow against the home (LISC, 2024)."),
}

# Homestead figures from the Franklin County Auditor's Homestead pages (checked October 2026). They change every year.
HOMESTEAD = {
    "exempt_value": "$29,000",       # senior / disabled / surviving spouse: this much of the home's value isn't taxed
    "veteran_value": "$58,000",      # 100% disabled veterans, no income limit
    "income_limit": "$41,000",       # Ohio modified adjusted gross income, for new 2026 applications
    "income_year": "2025",
    "deadline": "December 31",       # of the year you want the tax break for; late applications are accepted
}


# Plain-English meanings for the words the app uses, shown as "Words to know"
GLOSSARY = [
    ("Deed", "The paper, recorded with the County, that says who owns a home."),
    ("Title", "Legal ownership of a home. A 'clear title' means the County record matches who really owns it."),
    ("Tangled title (heirs' property)", "When an owner has died and the home was never moved into the living family's "
                                        "names. The family lives there, but can't prove they own it."),
    ("Transfer on Death affidavit", "A short Ohio form that names who gets the home when the owner dies, so no "
                                    "court is needed. It must be recorded while the owner is alive."),
    ("Probate", "The court process that settles a person's property after they die and moves it to the heirs."),
    ("Survivorship", "Words on a deed that mean the living owner automatically keeps the home when the other owner "
                     "dies."),
    ("Heir", "A family member who inherits property under Ohio law when there's no will or Transfer on Death form."),
    ("Notary", "A person who watches you sign and confirms it's really you. Many banks offer this for free."),
    ("Homestead exemption", "An Ohio property tax break for owners who are 65 or older, disabled, or a qualifying "
                            "surviving spouse, on the home they live in."),
]


def link(key: str) -> str:
    """Markdown link for a resource key."""
    name, url = LINKS[key]
    return f"[{name}]({url})"
