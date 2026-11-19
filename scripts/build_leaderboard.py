"""Build an offline leaderboard and dedicated player profile pages."""

import argparse
import json
import re
import shutil
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import quote

from leaderboard import build_player_profiles
from analyze_league import analyze, card_stats, BASIC_LANDS

ROOT = Path(__file__).resolve().parents[1]


def record(values):
    return '–'.join(map(str, values))


def trophy(count):
    count = int(count)
    if not count:
        return ''
    multiplier = f' (x{count})' if count > 1 else ''
    label = 'perfect finish' if count == 1 else 'perfect finishes'
    return f'<span class="trophies" role="img" aria-label="{count} {label}">🏆{multiplier}</span>'


def build_card_data(entries, coverage, images, image_prefix=''):
    boards = {key: card_stats(entries, board, include_basics=True)
              for key, board in [('all', None), ('mainboard', 'mainboard'), ('sideboard', 'sideboard')]}
    names = {row['card'] for row in boards['all']}
    return {
        'coverage': coverage, 'basics': sorted(BASIC_LANDS), 'boards': boards,
        'images': {name: metadata | {'image': image_prefix + metadata['image']}
                   for name, metadata in images.items() if name in names},
    }


def build_player_card_data(player, analysis, images):
    entries = [entry for entry in analysis['decklists'] if entry['competitorId'] == player['id']]
    missing = [entry for entry in analysis['coverage']['missing'] if entry['competitorId'] == player['id']]
    coverage = {'entries': len(player['events']), 'captured': len(entries), 'missing': missing}
    return build_card_data(entries, coverage, images, '../')


def render_matchups(player):
    rows = []
    for opponent in player['matchups']:
        boxes = []
        for match in opponent['matches']:
            wins, losses = match['wins'], match['losses']
            outcome = ('draw' if wins == losses else
                       'win-sweep' if (wins, losses) == (2, 0) else
                       'win-close' if wins > losses else
                       'loss-sweep' if (wins, losses) == (0, 2) else 'loss-close')
            score = f'{wins}–{losses}'
            result = 'Draw' if wins == losses else 'Win' if wins > losses else 'Loss'
            detail = (f'{result} {score} vs {opponent["name"]} · {match["event"]} · '
                      f'{match["date"]} · Round {match["round"]}'
                      + (f' · {match["draws"]} drawn game(s)' if match['draws'] else ''))
            boxes.append(
                f'<span class="match-box {outcome}" tabindex="0" aria-label="{escape(detail, quote=True)}">'
                f'<span aria-hidden="true">{score}</span>'
                f'<span class="match-tooltip" aria-hidden="true">{escape(detail)}</span></span>'
            )
        is_self = opponent.get('isSelf', False)
        results = ('<span class="matchup-self-label">You</span>' if is_self else
                   ''.join(boxes) or '<span class="matchup-unplayed">No matches</span>')
        column_class = 'matchup-column matchup-self' if is_self else 'matchup-column'
        rows.append(
            f'<li class="{column_class}"><div class="matchup-results">{results}</div><a class="matchup-player" href="{opponent["id"]}.html">'
            f'<span class="rank">#{opponent["rank"]}</span> {escape(opponent["name"])}</a>'
            f'</li>'
        )
    return ''.join(rows) or '<li class="empty">No league opponents yet.</li>'


def render_profile(player, template, styles, leaderboard_url, card_data, cloud_script):
    decks = ''.join(
        f'<tr><td>{escape(deck["name"])} {trophy(deck["trophies"])}</td>'
        f'<td>{deck["events"]}</td><td>{record(deck["matchRecord"])}</td>'
        f'<td>{record(deck["gameRecord"])}</td><td>{deck["matchWinRate"]:.1%}</td>'
        f'<td>{deck["gameWinRate"]:.1%}</td></tr>'
        for deck in player['decks']
    )
    opponents = ''.join(
        f'<tr><td><a href="{opponent["id"]}.html">{escape(opponent["name"])}</a></td>'
        f'<td>{sum(opponent["matchRecord"])}</td><td>{record(opponent["matchRecord"])}</td>'
        f'<td>{record(opponent["gameRecord"])}</td></tr>'
        for opponent in player['opponents']
    ) or '<tr><td colspan="4" class="empty">No reported opponents yet.</td></tr>'
    events = ''.join(
        f'<tr><td>{date.fromisoformat(event["date"]).strftime("%b %d, %Y")} {trophy(event["trophy"])}</td>'
        f'<td style="text-align:left">{escape(event["archetype"])}</td><td>{event["rank"]}</td>'
        f'<td>{record(event["matchRecord"])}</td><td>{record(event["gameRecord"])}</td>'
        f'<td class="points">{event["points"]}</td></tr>'
        for event in reversed(player['events'])
    )
    stats = [(player['rank'], 'season rank'), (player['points'], 'match points'),
             (len(player['events']), 'events played'), (len(player['decks']), 'decks played')]
    values = {
        'PLAYER_NAME': escape(player['name']), 'STYLES': styles,
        'LEADERBOARD_URL': escape(leaderboard_url, quote=True),
        'TROPHIES': trophy(player['trophies']), 'RECORD': record(player['matchRecord']),
        'WIN_RATE': f'{player["matchWinRate"]:.1%}',
        'SUMMARY': ''.join(f'<div class="stat"><strong>{n}</strong><span>{label}</span></div>' for n, label in stats),
        'DECK_ROWS': decks,
        'DECK_TOTAL': (
            f'<tr><th scope="row">Total</th><td>{len(player["events"])}</td>'
            f'<td>{record(player["matchRecord"])}</td><td>{record(player["gameRecord"])}</td>'
            f'<td>{player["matchWinRate"]:.1%}</td><td>{player["gameWinRate"]:.1%}</td></tr>'
        ),
        'OPPONENT_ROWS': opponents, 'EVENT_ROWS': events,
        'MATCHUP_ROWS': render_matchups(player),
        'CARD_DATA': json.dumps(card_data, ensure_ascii=False).replace('<', '\\u003c'),
        'CLOUD_SCRIPT': cloud_script,
    }
    return re.sub(r'__([A-Z_]+)__', lambda match: values[match[1]], template)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tournaments", type=Path, default=ROOT / "data/tournaments.json")
    parser.add_argument("--output", type=Path, default=ROOT / "leaderboard.html")
    parser.add_argument("--exports", type=Path, default=ROOT / "data/moxfield-exports")
    args = parser.parse_args()
    tournaments = json.loads(args.tournaments.read_text(encoding="utf-8"))
    players = build_player_profiles(tournaments)
    analysis = analyze(tournaments, args.exports)
    images = (json.loads((ROOT / 'data/scryfall-cards.json').read_text(encoding='utf-8'))
              if (ROOT / 'data/scryfall-cards.json').is_file() else {})
    card_data = build_card_data(analysis['decklists'], analysis['coverage'], images)
    card_data['events'] = analysis['events']
    cloud_script = (ROOT / 'web/card-cloud.js').read_text(encoding='utf-8')
    data = json.dumps(players, ensure_ascii=False).replace("<", "\\u003c")
    template = (ROOT / "web/leaderboard.html").read_text(encoding="utf-8")
    styles = (ROOT / 'web/styles.css').read_text(encoding='utf-8')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.parent.resolve() != ROOT and (ROOT / 'assets/cards').is_dir():
        shutil.copytree(ROOT / 'assets/cards', args.output.parent / 'assets/cards', dirs_exist_ok=True)
    args.output.write_text(template.replace('__STYLES__', styles).replace("__LEAGUE_DATA__", data), encoding="utf-8")
    card_template = (ROOT / 'web/cards.html').read_text(encoding='utf-8')
    card_json = json.dumps(card_data, ensure_ascii=False).replace('<', '\\u003c')
    (args.output.parent / 'cards.html').write_text(
        card_template.replace('__STYLES__', styles).replace('__CARD_DATA__', card_json)
        .replace('__CLOUD_SCRIPT__', cloud_script)
        .replace('__LEADERBOARD_URL__', escape(quote(args.output.name), quote=True)), encoding='utf-8')
    profile_template = (ROOT / 'web/player.html').read_text(encoding='utf-8')
    profile_dir = args.output.parent / 'players'
    profile_dir.mkdir(exist_ok=True)
    for player in players:
        (profile_dir / f'{player["id"]}.html').write_text(
            render_profile(player, profile_template, styles, '../' + quote(args.output.name),
                           build_player_card_data(player, analysis, images), cloud_script), encoding='utf-8')
    print(f"Built {args.output}, cards.html, and {len(players)} player pages in {profile_dir}")


if __name__ == "__main__":
    main()
