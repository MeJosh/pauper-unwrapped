"""Season standings from completed events; no decklist downloads required."""


def win_rate(record):
    total = sum(record)
    return record[0] / total if total else 0


def build_leaderboard(tournaments):
    players = {}
    for event in sorted(tournaments, key=lambda event: event["date"]):
        if event["status"] != "COMPLETE":
            continue
        games = {row["playerId"]: [0, 0, 0] for row in event["standings"]}
        for round_view in event["roundViews"]:
            for match in round_view["matches"]:
                if not match["reported"]:
                    continue
                for own, other in (("player1", "player2"), ("player2", "player1")):
                    player_id = match[f"{own}Id"]
                    if player_id in games:
                        record = games[player_id]
                        record[0] += match[f"{own}Wins"]
                        record[1] += match[f"{other}Wins"]
                        record[2] += match.get("draws", 0)
        for row in event["standings"]:
            player = players.setdefault(row["competitorId"], {
                "id": row["competitorId"], "name": row["name"],
                "matchRecord": [0, 0, 0], "gameRecord": [0, 0, 0], "events": [],
            })
            match_record = [row["wins"], row["losses"], row["draws"]]
            game_record = games[row["playerId"]]
            for key, record in (("matchRecord", match_record), ("gameRecord", game_record)):
                player[key] = [a + b for a, b in zip(player[key], record)]
            player["events"].append({
                "id": event["id"], "name": event["name"], "date": event["date"],
                "rank": row["rank"], "archetype": row["archetype"],
                "matchRecord": match_record, "gameRecord": game_record,
                "points": 3 * row["wins"] + row["draws"],
                "trophy": match_record == [3, 0, 0],
            })
    for player in players.values():
        player["points"] = 3 * player["matchRecord"][0] + player["matchRecord"][2]
        player["matchWinRate"] = win_rate(player["matchRecord"])
        player["gameWinRate"] = win_rate(player["gameRecord"])
        player["trophies"] = sum(event["trophy"] for event in player["events"])
    ordered = sorted(players.values(), key=lambda p: (
        -p["points"], -p["matchWinRate"], -p["gameWinRate"], p["name"],
    ))
    previous = None
    for index, player in enumerate(ordered, 1):
        score = (player["points"], player["matchWinRate"], player["gameWinRate"])
        player["rank"] = previous["rank"] if previous and score == previous_score else index
        previous, previous_score = player, score
    return ordered


def build_player_profiles(tournaments):
    """Group decks and actual opponents for each persistent competitor."""
    players = build_leaderboard(tournaments)
    by_id = {player['id']: player for player in players}
    opponents = {player['id']: {} for player in players}
    for event in sorted(tournaments, key=lambda event: event['date']):
        if event['status'] != 'COMPLETE':
            continue
        ids = {row['playerId']: row['competitorId'] for row in event['standings']}
        for round_view in event['roundViews']:
            for match in round_view['matches']:
                if not match['reported'] or match['bye']:
                    continue
                for own, other in (('player1', 'player2'), ('player2', 'player1')):
                    own_id, other_id = ids[match[f'{own}Id']], ids[match[f'{other}Id']]
                    opponent = opponents[own_id].setdefault(other_id, {
                        'id': other_id, 'name': by_id[other_id]['name'],
                        'matchRecord': [0, 0, 0], 'gameRecord': [0, 0, 0],
                        'matches': [],
                    })
                    wins, losses = match[f'{own}Wins'], match[f'{other}Wins']
                    opponent['matches'].append({
                        'wins': wins, 'losses': losses, 'draws': match.get('draws', 0),
                        'date': event['date'], 'event': event['name'],
                        'round': round_view['number'],
                    })
                    opponent['matchRecord'][0 if wins > losses else 1 if wins < losses else 2] += 1
                    for index, count in enumerate((wins, losses, match.get('draws', 0))):
                        opponent['gameRecord'][index] += count
    for player in players:
        decks = {}
        for event in player['events']:
            deck = decks.setdefault(event['archetype'], {
                'name': event['archetype'], 'events': 0, 'matchRecord': [0, 0, 0],
                'gameRecord': [0, 0, 0], 'trophies': 0,
            })
            deck['events'] += 1
            deck['trophies'] += event['trophy']
            for key in ('matchRecord', 'gameRecord'):
                deck[key] = [a + b for a, b in zip(deck[key], event[key])]
        for deck in decks.values():
            deck['matchWinRate'] = win_rate(deck['matchRecord'])
            deck['gameWinRate'] = win_rate(deck['gameRecord'])
        player['decks'] = sorted(decks.values(), key=lambda deck: (-deck['events'], deck['name']))
        player['opponents'] = sorted(opponents[player['id']].values(),
                                     key=lambda opponent: (-sum(opponent['matchRecord']), opponent['name']))
        player['matchups'] = [
            {'id': other['id'], 'name': other['name'], 'rank': other['rank'],
             'isSelf': other['id'] == player['id'],
             'matches': opponents[player['id']].get(other['id'], {}).get('matches', [])}
            for other in players
        ]
    return players
