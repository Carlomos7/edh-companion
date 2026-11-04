# Deck export formats: Moxfield, Archidekt and MTG Arena

Research into what text imports correctly into Moxfield, Archidekt and MTG Arena.
All sources accessed 2026-11-03. Items marked **(unconfirmed)** were not verified against a primary source, or were not tested by importing (nothing was pasted into any site).

## Summary

- **Moxfield text import works for the card lines.** Moxfield's own help gives `AMOUNT CARDNAME (SETCODE) NUMBER *F*` with the set, number and foil marker optional. Our `moxfield` lines match that shape. Two gaps: the commander is not marked by the paste (it is picked in the New Deck dialog), and `*E*` for etched is not in Moxfield's help.
- **Archidekt accepts our `moxfield` and `arena` text** in its Import menu, which says "Paste your deck (or Arena export) here". Its own syntax adds `1x`, lowercase set codes, `*F*`, `[Category]` and `# Category` headers. To set the commander, use its category syntax `[Commander{top}]` on the commander's line.
- **MTG Arena breaks on our `arena` output for this deck.** Many of our set codes are paper-only (PLST, SLD, MSC, MSH, PZA and others). A set code a card is not in gives a "card not found" error, and some Arena set codes differ from Scryfall's. Our `arena` output also carries `*F*`, which is not part of Arena's format. For Arena, export names only under `Commander` / `Deck` headers.
- **CSV:** Moxfield and Archidekt import CSV only into a collection, not into a deck. Moxfield needs exact column names (`Count`, `Name`, `Edition`, `Collector Number`, `Foil`, ...). Our column names do not match.
- **No official public API for creating decks** on either site. Moxfield says its API is private. Archidekt has an undocumented API that its developer allows people to use, with no docs and no stability promise. Arena has no deck API.

---

## 1. Moxfield deck import

### Line syntax

Moxfield's help page "Creating Decks" gives the paste format as `AMOUNT CARDNAME (SETCODE) NUMBER *F*` and says the set code, collector number and `*F*` are optional. Its examples are `1 Counterspell (CMR) 632 *F*`, `1 Sol Ring` and `1 Arcane Signet *F*`. A `.txt` file upload uses the same format. https://moxfield.com/help/help-articles/creating-decks

Moxfield uses Scryfall set codes. https://moxfield.com/help/help-articles/importing-collection

### Set code case

The deck help shows uppercase codes (`CMR`). The collection CSV example uses lowercase codes (`c21`, `oc21`). So Moxfield accepts both cases at least in CSV. https://moxfield.com/help/help-articles/importing-collection. That the deck paste also ignores case is **(unconfirmed)**, but our uppercase output matches the help example, so it is safe either way.

### Collector numbers with letters or dashes, and The List

Moxfield's CSV help says collector numbers are usually numbers, but "a letter or star (★)" is sometimes appended. https://moxfield.com/help/help-articles/importing-collection. It does not mention dashes.

The List uses Scryfall set `plst` with numbers like `XLN-117`. MythicHub documents a Moxfield export line `1 Revel in Riches (PLST) XLN-117`, which shows Moxfield itself writes this form. https://mythichub.com/help/importing-decklists. A tool author reports that a Moxfield collection CSV round trip kept a The List card (`plst DDC-49`) and an etched finish. https://github.com/StepKie/MtgCsvHelper/blob/develop/MtgCsvHelper/Resources/SampleCsvs/Tests/SITE_BEHAVIOR.md. Our `(PLST) ULG-14` and `10a` therefore look correct. Whether the deck paste importer accepts dashed numbers is **(unconfirmed)** from Moxfield's own pages.

### Foil and etched

`*F*` is documented by Moxfield. https://moxfield.com/help/help-articles/creating-decks

`*E*` for etched is not on Moxfield's help pages. Several third-party importers that read Moxfield exports document `*F*` or `*E*` at the end of the line, which suggests Moxfield writes `*E*` itself: https://silvane.app/docs/import-export/importing, https://mythichub.com/help/importing-decklists. Moxfield reading `*E*` on paste is **(unconfirmed)**.

### Marking the commander

The help says the New Deck dialog asks for the format and "a Commander / Oathbreaker / Signature spell", which can be changed later. It does not describe a `Commander` header or a `*CMDR*` marker in the paste. https://moxfield.com/help/help-articles/creating-decks

MythicHub says Moxfield text exports "do not map commander roles automatically". https://mythichub.com/help/importing-decklists. Silvane instead says Moxfield exports use colon headers such as `COMMANDER:` and `SIDEBOARD:`. https://silvane.app/docs/import-export/importing. The two disagree, so whether Moxfield's paste reads a `COMMANDER:` header is **(unconfirmed)**. `SIDEBOARD:` as a header in Moxfield exports is shown by both sources.

What this means for us: with no marker, our commander (the first line) lands in the main deck unless the user picks it in the New Deck dialog. A `*CMDR*` marker is not documented anywhere I found.

### Silent substitution

A tool author reports that Moxfield's collection CSV import silently matches a wrong collector number to another valid printing of the same name and set, with no error. https://github.com/StepKie/MtgCsvHelper/blob/develop/MtgCsvHelper/Resources/SampleCsvs/Tests/SITE_BEHAVIOR.md. A Moxfield feedback post reports Moxfield picking a different SLD printing when the collector number had a suffix it did not know (`708e`). https://moxfield.nolt.io/1009. Whether the deck paste does the same is **(unconfirmed)**, but a bad number should be assumed to land on a different printing, not to fail.

---

## 2. Archidekt deck import

### What the Import menu accepts

Archidekt's FAQ says the Import menu lists the accepted formats under "Formatting Examples" and reports any errors after "Save Changes". https://archidekt.com/faq

I read that menu in the public sandbox (no login, nothing pasted). https://archidekt.com/sandbox. Its text area says "Paste your deck (or Arena export) here". The examples are:

- `2 Sensei's Divining Top` and `2x Sensei's Divining Top` (both quantity forms work)
- `1 Mountain (DOM) 263` (set and collector number)
- `1x Path to Exile (cmm) [Removal] ^To Remove,#FF0000^` (category in square brackets, colour label in carets, lowercase set code)
- `# Sideboard` on its own line, followed by cards, to put a group of cards in one category

The uppercase `DOM` and lowercase `cmm` examples suggest set code case does not matter.

### Archidekt's own export syntax

Archidekt's Export dialog on a public deck shows the line form `1x Example Card (set) 123 *F* [Example category] ^Buy,#0066ff^`. https://archidekt.com/decks/27905725 (Export deck dialog). So `*F*` is Archidekt's foil marker. An Archidekt news post also says "Foil tags again properly set a card's foiling" in the text editor. https://archidekt.com/news/660198

Archidekt has an etched finish (the `E` key sets a card to etched). https://archidekt.com/news/3108703. The text marker `*E*` is documented only by third parties reading Archidekt exports: https://mythichub.com/help/importing-decklists, https://silvane.app/docs/import-export/importing. **(unconfirmed)** from Archidekt.

### Commander and other boards

Third-party importers document Archidekt export lines such as `1x Xyris, the Writhing Storm (dmc) 175 [Commander{top}]` and `[Maybeboard{noDeck}]`. The `{top}` flag marks a "premier" category such as Commander and `{noDeck}` marks out-of-deck categories. https://mythichub.com/help/importing-decklists, https://silvane.app/docs/import-export/importing. Archidekt's own news describes "Premier categories (such as Commander)" shown at the top of the deck. https://archidekt.com/news/3108703. That a pasted `[Commander{top}]` creates the commander category on a fresh deck is **(unconfirmed)** by test, but it is the form Archidekt's own exports use.

Whether a plain `# Commander` header, or an Arena `Commander` section, sets the commander (and not just a category named Commander) is **(unconfirmed)**.

### The List and dashed numbers

Not documented by Archidekt. Archidekt uses Scryfall data as its source of truth, per its developer. https://archidekt.com/forum/thread/11072025. So `(plst) ULG-14` should match, **(unconfirmed)**.

---

## 3. MTG Arena import

### Format

Wizards' support article shows plain `count name` lines and says missing cards can be crafted after import. It does not document set codes, sections or errors. https://mtgarena-support.wizards.com/hc/en-us/articles/360049857771-Importing-a-Deck

Arena's own export uses `count Name (SET) number`. For Brawl it adds `Commander` and `Deck` keyword lines, with a blank line between, for example `Commander` / `1 Alela, Artful Provocateur (ELD) 324` / blank / `Deck` / ... . https://magicarena.fandom.com/wiki/Deck_Import. So our `Commander` / blank / `Deck` layout is right **(community wiki, not Wizards)**.

### Paper-only set codes

A line whose set code does not hold that card gives a "card not found" error, and the fix is to change or remove the set. Draftsim's example is Ardenvale Tactician listed as (WAR). https://draftsim.com/mtg-arena-import-deck/. Arena also uses its own codes for some sets: its export of Dominaria cards shows `(DAR)`, where Scryfall uses `DOM`. https://magicarena.fandom.com/wiki/Deck_Import

So lines such as `(PLST) ULG-14`, `(SLD) 1727`, `(MSC) 122` or `(PZA) 17` will fail. Whether one bad line fails the whole import or only that card is **(unconfirmed)**. A bare name with no set lets Arena pick its own printing. https://mtgazone.com/import/

### Foil markers

`*F*` is not part of Arena's import or export format in any source above. A line ending in `*F*` is likely to be read as part of the name or give "invalid line". https://draftsim.com/mtg-arena-import-deck/ describes the "invalid line" error. **(unconfirmed)** by test.

### Cards not on Arena

Brawl (100 cards, formerly Historic Brawl) uses only cards on Arena. https://magic.wizards.com/en/formats/brawl. A paper-only card gives the "card not found" error above. https://draftsim.com/mtg-arena-import-deck/

---

## 4. CSV import

### Moxfield

Moxfield imports CSV into a collection or binder, not into a deck. Deck import takes paste or `.txt` only. https://moxfield.com/help/help-articles/creating-decks

Collection CSV headers must be spelled exactly, case included, in any order: `Count`, `Name`, `Edition`, `Condition`, `Language`, `Foil`, `Collector Number`, `Alter`, `Playtest Card`, `Purchase Price`. Only `Name` is required. `Edition` is the Scryfall set code. `Foil` is blank, `foil` or `etched`. `Purchase Price` is a plain number with no currency sign. https://moxfield.com/help/help-articles/importing-collection

### Archidekt

Archidekt imports CSV into a collection. You either pick a preset for a known site or set each column by hand. With manual columns it warns of ambiguity unless it has a Scryfall ID, or a card name with a set and collector number. Ambiguous rows can be skipped or tagged "Unsure". https://archidekt.com/news/5891613

Its own collection export uses columns such as `Quantity`, `Name`, `Finish`, `Edition Code`, `Scryfall ID`, `Collector Number`. https://docs.scryme.app/import/formats **(third party)**

---

## 5. Official APIs for creating decks

**Moxfield:** No. Its FAQ says "No, our API is not public". On rare occasions it helps personal, non-commercial or community projects that email support@moxfield.com. https://moxfield.com/help/help-articles/faq

**Archidekt:** No official, documented API. The developer says the API is open for reading and people may use it, but there are no docs because of how often it changes. Too much load may lead them to lock it down. https://archidekt.com/forum/thread/40353, https://archidekt.com/forum/thread/2832338. Writing (creating decks) needs a login token. Third-party CLIs do it through the unofficial API. https://github.com/forsmark/archidekt-cli

**MTG Arena:** No deck-creation API. The only route is the in-client Import button. https://mtgarena-support.wizards.com/hc/en-us/articles/360049857771-Importing-a-Deck

---

## 6. Recommended changes to `export`

1. **`moxfield`: keep the card-line format.** It matches Moxfield's documented syntax, and The List numbers match Moxfield's own export form. Say in `import_into` that the user must pick the commander in Moxfield's New Deck dialog. Do not add `*CMDR*`, which no source documents.
2. **Add an `archidekt` format:** `1x Name (set) cn *F* [Category]`, with the commander line as `1x Anti-Venom, Horrifying Healer (spm) 1 [Commander{top}]`, etched as `*E*`. Then stop telling users that the `moxfield` output is for Archidekt.
3. **`arena`: drop set, collector number and `*F*`.** Write `Commander` / `1 Name` / blank / `Deck` / `1 Name` ... with names only, so Arena picks its own printings. Optionally keep `(SET) cn` only when the set is known to be on Arena, but the names-only form is simpler and never fails on set codes.
4. **`csv`: offer a Moxfield-collection variant**, or rename columns to `Count,Name,Edition,Collector Number,Foil,Purchase Price`. Write `Foil` as blank, `foil` or `etched` (not `nonfoil`). Add a `Scryfall ID` column, which removes Archidekt's ambiguity. Note that this imports into a collection, not a deck.
5. **Confirm by hand before relying on items 2 and 3.** One test paste into each site by the user would confirm the **(unconfirmed)** points: Moxfield `*E*` and dashed numbers, Archidekt `[Commander{top}]`, and how Arena handles one bad line.
