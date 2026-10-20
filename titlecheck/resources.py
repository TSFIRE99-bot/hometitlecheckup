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
}

CONTACTS = {
    "recorder": ("Franklin County Recorder", "373 S. High St., 18th floor, Columbus, OH 43215", "(614) 525-3930"),
    "probate": ("Franklin County Probate Court (procedure questions, not legal advice)", "", "(614) 525-3894"),
    "lasco": ("Legal Aid of Southeast and Central Ohio", "lasco.org/apply", "(614) 221-7201"),
}

FACTS = {
    "ohio_count": "Ohio has an estimated 9,000 heirs' properties (Greater Ohio Policy Center, 2024).",
    "ohio_value": "Those homes hold about $313 million in family wealth that clear titles could unlock (LISC, 2024).",
    "blocked": ("Without a clear title, families can't get home-repair financing, claim the homestead tax break, "
                "get disaster aid, or borrow against the home (LISC, 2024)."),
}


def link(key: str) -> str:
    """Markdown link for a resource key."""
    name, url = LINKS[key]
    return f"[{name}]({url})"
