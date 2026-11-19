"""Join Moxfield plain-text exports to the tournament export and compute recap stats."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from leaderboard import build_leaderboard

ROOT = Path(__file__).resolve().parents[1]
CARD_LINE = re.compile(r"([1-9][0-9]*)\s+(.+)")
BASIC_LANDS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}
BASIC_LANDS |= {f"Snow-Covered {name}" for name in BASIC_LANDS - {"Wastes"}}


def parse_deck(text):
    boards = {"mainboard": Counter(), "sideboard": Counter()}
    board = "mainboard"
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.upper() == "SIDEBOARD:":
            board = "sideboard"
            continue
        match = CARD_LINE.fullmatch(line)
        if not match:
            raise ValueError(f"Unrecognized deck line {line!r}")
        quantity, name = match.groups()
        boards[board][name] += int(quantity)
    if sum(boards["mainboard"].values()) < 60:
        raise ValueError("Main deck has fewer than 60 cards")
    if sum(boards["sideboard"].values()) > 15:
        raise ValueError("Sideboard has more than 15 cards")
    return {board: dict(sorted(cards.items())) for board, cards in boards.items()}


def card_stats(entries, board=None, include_basics=False):
    """Count registrations, merging boards before counting whole-deck appearances."""
    appearances, copies = Counter(), Counter()
    for entry in entries:
        cards = (Counter(entry['mainboard']) + Counter(entry['sideboard'])
                 if board is None else entry[board])
        appearances.update(cards.keys())
        copies.update(cards)
    return [
        {"card": name, "decks": appearances[name], "copies": copies[name]}
        for name in sorted(appearances, key=lambda name: (-appearances[name], name))
        if include_basics or name not in BASIC_LANDS
    ]


def analyze(tournaments, exports):
    entries, missing, events = [], [], []
    players = defaultdict(lambda: {"entries": 0, "archetypes": set()})
    archetypes, head_to_head = Counter(), Counter()
    for event in sorted(tournaments, key=lambda event: event["date"]):
        if event['status'] != 'COMPLETE':
            continue
        standings = event["standings"]
        matches = [
            match for round_view in event["roundViews"] for match in round_view["matches"]
            if match["reported"] and not match["bye"]
        ]
        ids = {row["playerId"]: row["competitorId"] for row in standings}
        for match in matches:
            pair = tuple(sorted((ids[match["player1Id"]], ids[match["player2Id"]])))
            head_to_head[pair] += 1
        events.append({
            "id": event["id"], "date": event["date"], "status": event["status"],
            "entries": len(standings), "playedMatches": len(matches),
            "drawnMatches": sum(match["player1Wins"] == match["player2Wins"] for match in matches),
            "rankOne": next((row["name"] for row in standings if row["rank"] == 1), None),
        })
        for row in standings:
            archetypes[row["archetype"]] += 1
            player = players[row["competitorId"]]
            player["name"] = row["name"]
            player["entries"] += 1
            player["archetypes"].add(row["archetype"])
            url = row.get("deckUrl") or ""
            deck_id = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
            metadata = {
                "eventId": event["id"], "date": event["date"], "rank": row["rank"],
                "competitorId": row["competitorId"], "player": row["name"],
                "archetype": row["archetype"], "url": url,
            }
            if not re.fullmatch(r"[A-Za-z0-9_-]+", deck_id):
                missing.append(metadata)
                continue
            path = exports / f"{deck_id}.txt"
            if not path.is_file():
                missing.append(metadata)
                continue
            try:
                entries.append(metadata | parse_deck(path.read_text(encoding="utf-8")))
            except ValueError as error:
                raise ValueError(f"{path}: {error}") from error

    return {
        "leaderboard": build_leaderboard(tournaments),
        "events": events,
        "coverage": {"entries": sum(archetypes.values()), "captured": len(entries), "missing": missing},
        "archetypes": dict(sorted(archetypes.items(), key=lambda item: (-item[1], item[0]))),
        "players": {
            key: value | {"archetypes": sorted(value["archetypes"])}
            for key, value in sorted(players.items())
        },
        "headToHead": [
            {"players": [players[key]["name"] for key in pair], "matches": count}
            for pair, count in head_to_head.most_common()
        ],
        "mainboardCards": card_stats(entries, "mainboard"),
        "sideboardCards": card_stats(entries, "sideboard"),
        "allCards": card_stats(entries),
        "decklists": entries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tournaments", type=Path, default=ROOT / "data/tournaments.json")
    parser.add_argument("--exports", type=Path, default=ROOT / "data/moxfield-exports")
    args = parser.parse_args()
    tournaments = json.loads(args.tournaments.read_text(encoding="utf-8"))
    print(json.dumps(analyze(tournaments, args.exports), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
