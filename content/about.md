<!--
  EDIT ME: this file is the text of the About page (/about).

  How to edit on GitHub: open this file, click the pencil icon, change the text, then click "Commit changes".
  Vercel updates the live site about a minute later.

  - "# " is the page title. Text before the first "##" is the introduction at the top.
  - Every "## " heading starts a new section (a card). Add, remove or reorder sections freely.
  - The {word} at the end of a heading picks its icon. Options: heart, users, map, shield, info, file, book, home,
    help, pin, clock, dollar, phone, calendar, alert, user. Leave it off for no icon.
  - **bold**, *italic*, [link text](https://...), "- " bullets and "1. " numbered lists all work.
  - Notes like this one, between the comment marks, never show on the site.
  - The list of sources at the bottom of the page is added automatically from titlecheck/resources.py.
-->

# About HomeKeep

A home is the biggest thing most families ever pass down. In Columbus, many families lose that wealth not because of
debt or a bad deal, but because one form was never filed. We built HomeKeep so any family can find out, in plain
English and for free, whether their home is protected, and what to do next.

## Who it's for {heart}

Homeowners, especially older homeowners, and families who inherited a home. It's written for people who have never
talked to a lawyer, works on a phone, and has a larger-text button.

## Why it matters here {users}

Heirs' property is concentrated in neighborhoods that faced long-term disinvestment, where families had less access to
lawyers and estate planning (Greater Ohio Policy Center, 2024). A clear title makes it much easier for a family to
get repair loans, disaster aid and the homestead tax break, and to pass the home on.

## How it works {map}

1. You type an address. The app asks the Franklin County Auditor's public parcel records (an ArcGIS REST service)
   whose name is on the tax record and when the home last changed hands. That name is for tax bills. It isn't proof
   of who legally owns the home, so the app asks you the rest.
2. You answer a few yes / no questions, like whether everyone on the deed is living.
3. Rules based on Ohio law (Transfer on Death affidavits, survivorship deeds, and Franklin County Probate Court's
   small-estate options) turn the answers into a status, a plain-English summary written for you, and a step-by-step
   roadmap with time, cost and where to go for each step.
4. The optional Homestead Benefits Check estimates the property tax savings for the home's own tax district, using the
   County Auditor's published figures, and shows how and when to apply.
5. "Who would inherit?" shows how Ohio law would split the home, how many people would share it, and what each share
   of the home's value comes to. Value isn't equity: any mortgage, liens or unpaid taxes come off first.
6. "Free help near you" maps the free and official offices that handle each step.

## Privacy and safety by design {shield}

- One address at a time. The app never builds lists or maps of homes that might have tangled titles, because people
  who prey on heirs' property could misuse them.
- Neighbors on the map only show what the County's own public map shows, never a title status.
- HomeKeep doesn't store what you type. The free checkup has no accounts and no database, and roadmap check marks
  stay on your own device.
- Some things do leave your browser. The address you type goes to the Franklin County Auditor's map service to find
  the record. Pages load fonts from Google Fonts, and the maps load code and map pictures from outside services
  (jsDelivr, cdnjs, code.jquery.com, the Bootstrap CDN, OpenStreetMap and Esri). Those services see your IP address.
  Our host, Vercel, keeps standard request logs (which page, when, and from what IP address) for a limited time.
- No ads and no analytics. HomeKeep never sells or shares what you type.

## Limits {info}

- General information, not legal advice. Every plan points to free legal help.
- Franklin County only (for now). County records can lag behind recent filings.
- The app can't see whether someone has died; it asks you. Savings are the Auditor's estimates.

## Built by {users}

- **Tejas Menneni**, New Albany High School, 12th grade
- **Satvik Surapaneni**, Olentangy High School, 12th grade
- **Sutton Sykes**, New Albany High School, 12th grade
- **Naman Soni**, Olentangy High School, 12th grade

## Built with {file}

Python, HTML / CSS / JavaScript, and pytest, hosted on Vercel. 
Map tiles from OpenStreetMap contributors and Esri World Imagery. 
Parcel data and homestead estimates from the Franklin County Auditor. 
The text is from Atkinson Hyperlegible.

## Use of AI tools {info}

<!-- 
  We had a few technical issues to overcome. One of them was translating the app into languages other than English. We were struggling to get the translation done manually on our menus as it was taking too long and was messing up our code structure. We decided to use GitHub Copilots AI tool to help with our translations. It translated all of our text files quickly into multiple languages and kept our core code safe. We also used Google Earth API to process the satellite images. 
-->
 We had a few technical issues to overcome. One of them was translating the app into languages other than English. We were struggling to get the translation done manually on our menus as it was taking too long and was messing up our code structure. We decided to use GitHub Copilots AI tool to help with our translations. It translated all of our text files quickly into multiple languages and kept our core code safe. We also used Google Earth API to process the satellite images.

