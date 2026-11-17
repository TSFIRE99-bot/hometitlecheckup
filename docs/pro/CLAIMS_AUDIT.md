# Public claims audit

Checked November 17, 2026, on branch `homekeep-pro`. This is a student team's reading of public sources, not legal
review. A licensed Ohio attorney should read the public pages and this file before HomeKeep is shown to firms as
accurate.

## Sources checked

| Source | What it says that matters here | Checked |
|---|---|---|
| [ORC 5302.22](https://codes.ohio.gov/ohio-revised-code/section-5302.22) | A Transfer on Death designation affidavit only works if it is recorded before the owner dies; a married owner's spouse must sign a statement that their dower rights are subordinate. | Nov 17, 2026 (search summary of the official page) |
| [ORC 5302.222](https://codes.ohio.gov/ohio-revised-code/section-5302.222) | After the owner dies, the beneficiary records an affidavit of confirmation with a death certificate. | Nov 17, 2026 (search summary) |
| [ORC 5302.221](https://codes.ohio.gov/ohio-revised-code/section-5302.221) | The recorder gives the beneficiary a Medicaid estate recovery form before recording the transfer. | Nov 17, 2026 (search summary) |
| [ORC Chapter 5307](https://codes.ohio.gov/ohio-revised-code/chapter-5307) | Co-owners can ask the common pleas court for partition; the court can order a sale; inherited land generally can't be partitioned within a year of death unless debts are paid or secured. | Nov 17, 2026 (search summary) |
| [Franklin County Recorder fees](https://www.franklincountyohio.gov/Agency-Directory/Recorder/Real-Estate/Recording-Fees) | $34 for the first two pages, $8 per extra page, per ORC 317.32. Some other Ohio counties now list $39. | Nov 17, 2026 (page read directly) |
| [FEMA: verifying home ownership](https://www.fema.gov/assistance/individual/after-applying/verifying-home-ownership-occupancy) | FEMA accepts a will or an affidavit of heirship with a death certificate, tax bills, repair receipts and court documents as proof of ownership, and a signed self-declaration as a last resort in some situations. | Nov 17, 2026 (page read directly) |
| [FEMA policy memo, Sept 2, 2021](https://www.fema.gov/sites/default/files/documents/fema_iappg-policy-amendments-memo.pdf) | Introduced the self-declarative statement for heirship homes. | Nov 17, 2026 (search summary; PDF not opened) |

"Search summary" means we read a search tool's summary of the official page rather than the full text. Before any
firm relies on a point, someone should open the statute itself.

## Claims and what changed

| Where | Old wording | Problem | New wording (summary) |
|---|---|---|---|
| Footer, home page, inheritance page, About | "Nothing you type is saved." | Too broad. Our server stores nothing, but the address goes to the County's ArcGIS service, pages call Google Fonts and map CDNs, and Vercel keeps request logs. | "HomeKeep doesn't store what you type," with a link to an About section that lists every outside service and the Vercel logs. |
| Learn page, inheritance chart | "Every one of them has to be found and has to sign before the home can be sold..." | Reads as a universal rule. Partition (ORC 5307), probate sale and quiet title cases can resolve a home without every signature. | "To sell or refinance the usual way, all of them generally have to be found and sign. Otherwise it takes a court case." |
| Learn page, About, results page facts, README | "Families can't ... get disaster aid" | FEMA accepts a will or heirship affidavit with a death certificate, and a self-declaration as a last resort. | "Families often have trouble getting ... disaster aid," plus a FEMA example on the Learn page. |
| Home page stat, Learn page, inheritance callout | "1 form ... can prevent it, for a $34 fee"; "the home goes straight to the people named, with no probate" | Presented one form as the universal fix. The $34 fee is Franklin County's. Beneficiaries still record a confirmation affidavit; the spouse signs too; debts and estate recovery still apply. | "Can often avoid probate. Recording it costs $34 in Franklin County," and the Learn page lists the spouse statement, the confirmation affidavit and that the form doesn't settle debts. |
| Inheritance calculator, About, Learn, README | "$X of family wealth is **locked**"; "One heir can use all of the home's equity"; "$313 million in family wealth" | Treated market value as equity and as money the family has. | "$X of home value is tied up until the heirs agree"; the value field says value isn't equity; the $313 million is described as property value. |
| About page | "asks ... who is on the deed" | The Auditor's owner field is a tax-roll name, not proof of title. | "Whose name is on the tax record ... It isn't proof of who legally owns the home, so the app asks you the rest." |

Spanish and Somali versions of every changed sentence were updated in `tools/es.txt`, `tools/so.txt` and the
`content/*.es.md` and `content/*.so.md` files. They are machine-assisted and still need review by native speakers.

## Left as is, with reasons

- "The home is probably still legally in the name of someone who died" appears only after the visitor answers that
  an owner died. The app never infers a death from the record; the About page says so.
- "The County lists an **estate** as the owner. That usually means the owner died..." says "usually" and the
  visitor still answers the questions.
- The homestead note says families "usually can't apply until the title is in their name." That matches how the
  Auditor's forms describe eligibility, but an Auditor's office or attorney should confirm it.
- The 9,000 homes and $313 million figures come from Greater Ohio Policy Center and LISC (2024) and are labeled as
  estimates with sources.

## HomeKeep Pro wording rules

- Never describe an Auditor owner field as proof of title. The Pro case page shows the attached Auditor record with its parcel link, retrieval
date and a note that the owner field is a tax record, not proof of title.
- Never say a person has died unless staff recorded it from a document or a family report, and label which.
- Packets say "Prepared for professional review" and never "verified," "certified" or "approved by an attorney"
  unless a named attorney at the firm approved that item inside HomeKeep.
