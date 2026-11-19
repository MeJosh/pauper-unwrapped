# Pauper Unwrapped

The league export covers six completed events from June 6 to November 15, 2026. Across 46 entries, 15 players registered 24 archetype labels and played 63 reported matches, including six draws. The match count excludes 12 byes. November's status was updated locally after the organizer confirmed completion.

## Stories for the recap

- **The league's signature four-of.** Malevolent Rumble appeared in 14 of 46 main decks. Every one ran the full four copies, for 56 copies in total. Ichor Wellspring and Nihil Spellbomb tied for second by deck count at 12 each. These rankings exclude basic lands.
- **The sideboard MVP.** Breath Weapon showed up in 16 sideboards, the most of any card, with 37 copies. Ancient Grudge and Nihil Spellbomb tied for second at 13 lists each.
- **Six events, six decks.** Sam E and Josh E both played every event. Sam registered a different archetype each time and Josh registered five distinct archetypes.
- **Three straight first-place finishes.** Brenden B finished first in September, October, and November. Naya Gates was the most-registered archetype with five entries. Gruul Eldrazi and UWx Familiar tied for second at four.
- **Sam's recurring opponents.** Sam E faced Jens H four times and Josh E four times. Those pairs tied for the most meetings in the league.

## Decklist capture and analysis

The source links are in `data/tournaments.json`. The captured card quantities are in `data/moxfield-exports/<deck-id>.txt`. Direct HTTP requests to Moxfield returned 403 during collection, so the capture used the browser's deck pages. For a new event, open each deck link, choose **Download → Copy Plain Text**, and save the text using the ID at the end of the URL as the filename. The format is one quantity and card name per line followed by a `SIDEBOARD:` heading and the sideboard rows. Two existing lists were transcribed from Moxfield's card quantity panel when the export dialog did not open.

Run from the repository root with Python 3.9 or later.

```sh
python3 scripts/analyze_league.py > league-insights.json
```

The output includes the normalized decklists, card appearances and copy counts by board, event totals, player participation, and head-to-head meeting counts. Card appearances count a card once per deck per board. Archetypes come directly from the standings labels.

Coverage is 46 of 46 entries. The organizer supplied the plain-text export for Jens H's November UWx Familiar list. Moxfield lists reflect what the links showed at capture time and may have been edited since the events.

## Local leaderboard

The site is published at https://joshelliott.me/pauper-unwrapped/ using GitHub Pages from the root of `main`. Rebuild the generated HTML before committing changes; pushing to `main` publishes the updated files. `index.html` opens the leaderboard, and `.nojekyll` keeps the site served as static files.

Open `matchups.html` for every player’s matchup chart together, ordered by season placement using the same ranking and tie rules as the leaderboard. Links from the leaderboard, card popularity page, and player profiles lead to this view. Its **Show self on every chart** checkbox toggles the highlighted self column across all charts; player names link to their profiles.

Every player profile includes a **Matchups** chart. All players appear along the X axis in season rank order, including players not yet faced and the profile player, whose empty column is highlighted and marked “You”. The **Show self** checkbox above the chart is checked by default; uncheck it to hide that column. One box represents each reported head-to-head match, stacked vertically from oldest at the bottom to newest at the top, with the score from the profile owner's perspective: muted green for 2–1 or 1–0 wins, saturated green for 2–0 wins, saturated red for 0–2 losses, muted red for 1–2 or 0–1 losses, and grey for draws. Hover or keyboard-focus a box for its event, date, and round. Byes and incomplete events are excluded.

Every player profile includes a **Card cloud** section built only from that player’s event registrations. It uses the same compact image packing as the league cloud, with search, board filters, a basic-land toggle, and top-30/top-60/all-card options. Image area reflects total copies across their captured lists, including repeat registrations; image sizes are relative within each player’s selection. Coverage reports any missing lists. The shared renderer is `web/card-cloud.js`, embedded into generated pages so they still work offline.

Open `cards.html` for the league-wide card popularity breakdown, also linked from the leaderboard and player profiles. Search cards, switch between entire-deck, main-deck, and sideboard counts, include basic lands, or sort by deck count, deck share, copies, and average copies per using deck. Switch to **Card cloud** to see Scryfall card images with area proportional to total copies, with top-30, top-60, or all-card views. Hover or keyboard-focus a card for its counts; select it to open its Scryfall page. The cloud follows the same search, board, and basic-land filters as the table. Entire-deck appearances count each card once per event entry even when it occurs in both boards. Repeated registrations count separately. Percentages use captured lists from completed events; missing lists are reported and excluded. These are deck registration statistics, not in-game usage statistics.

Card images and their source links are cached in `assets/cards/` and `data/scryfall-cards.json`. The cloud works offline and does not call the Scryfall API from the browser. Images show representative printings, rather than the specific editions registered; double-faced cards show their front face. Names remain available as accessible labels and image-error fallbacks. Scryfall supplies the images; card imagery belongs to Wizards of the Coast.

After adding new decklists, fetch any missing images, then rebuild. The fetch sends card names only to Scryfall's collection endpoint in batches of up to 75, caches metadata, and downloads images with at most four concurrent CDN requests. Existing images are reused. Ordinary builds require no network access.

```sh
python3 scripts/fetch_card_images.py
python3 scripts/build_leaderboard.py
```

Across all 46 captured entries, excluding basic lands, Nihil Spellbomb leads with 18 decks (39.1%) and 46 copies. Breath Weapon follows with 16 decks (34.8%) and 38 copies across both boards; Malevolent Rumble appears in 14 decks (30.4%), totaling 56 copies.

Open `leaderboard.html` in your browser. It works offline, with player search and sortable columns. Select a player to open their dedicated page in `players/<competitor-id>.html`, with decks played, opponent records, and event history. Opponent names link to their own profiles. A single trophy marks a 3–0 finish; `(x2)` beside it means two finishes.

Rebuild the leaderboard, card breakdown, and all player pages after changing the tournament export or captured decklists:

```sh
python3 scripts/build_leaderboard.py
```

The default season ranking uses **total match points: 3 per win, 1 per draw**. This rewards both success and participation. Match win percentage, then game win percentage, break ties; equal results share a rank. Sorting by win percentage offers an attendance-independent comparison. Percentages are wins divided by total results, including draws in the denominator, matching the source player list. Byes count as awarded wins and game scores. Only completed events contribute. A trophy requires exactly 3–0–0, including byes, rather than simply first place.

The same computed standings are included as `leaderboard` in the analysis JSON. Edit `web/leaderboard.html`, `web/player.html`, `web/cards.html`, `web/matchups.html`, `web/matchup-chart.html`, and `web/styles.css` for presentation changes and `scripts/leaderboard.py` for scoring and profile aggregation, then rebuild the HTML. Styles are embedded into each output page, so the generated files need no server or asset downloads. Keep the `players` and `assets` folders beside the leaderboard when moving the site.

Deck summaries group entries by the source archetype label. Opponent records count reported, non-bye matches from completed events and show results from the profile owner's perspective; awarded byes remain included in season, deck, and event records.

Check scoring, bye handling, completed-event filtering, ties, and trophy rules with:

```sh
python3 -m unittest discover -s tests -v
```
