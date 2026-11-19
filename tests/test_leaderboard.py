"""Check season scoring and trophy rules against export and edge cases."""

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from leaderboard import build_leaderboard, build_player_profiles
from build_leaderboard import render_matchups


class LeaderboardTests(unittest.TestCase):
    def setUp(self):
        self.events = json.loads((ROOT / 'data/tournaments.json').read_text())

    def test_source_totals_and_trophies(self):
        players = build_leaderboard(self.events)
        self.assertEqual(len(players), 15)
        self.assertEqual([(p['name'], p['points']) for p in players[:3]],
                         [('Brenden B', 34), ('Josh E', 31), ('Sam E', 30)])
        self.assertEqual(players[0]['gameRecord'], [23, 8, 2])
        self.assertEqual(players[1]['gameRecord'], [24, 16, 1])
        self.assertEqual({p['name']: p['trophies'] for p in players if p['trophies']},
                         {'Brenden B': 2, 'Sam E': 1, 'Jens H': 1})
        november = next(e for e in players[0]['events'] if e['date'] == '2026-11-15')
        self.assertEqual(november['rank'], 1)
        self.assertFalse(november['trophy'])
        for p in players:
            self.assertAlmostEqual(p['matchWinRate'], p['matchRecord'][0] / sum(p['matchRecord']))

    def test_completed_only_and_empty(self):
        events = copy.deepcopy(self.events)
        for e in events:
            e['status'] = 'IN_PROGRESS'
        self.assertEqual(build_leaderboard(events), [])
        self.assertEqual(build_leaderboard([]), [])

    def test_byes_and_unreported_games(self):
        june = next(copy.deepcopy(e) for e in self.events if e['date'] == '2026-06-06')
        alex = next(p for p in build_leaderboard([june]) if p['name'] == 'Alex M')
        self.assertEqual(alex['matchRecord'], [1, 1, 1])
        self.assertEqual(alex['gameRecord'], [4, 3, 1])
        unreported = copy.deepcopy(june['roundViews'][0]['matches'][0])
        unreported['reported'] = False
        june['roundViews'][0]['matches'].append(unreported)
        self.assertEqual(alex, next(p for p in build_leaderboard([june]) if p['name'] == 'Alex M'))

    def test_equal_scores_share_rank(self):
        e = copy.deepcopy(self.events[0])
        e['roundViews'] = []
        for row in e['standings']:
            row.update(wins=0, losses=0, draws=0)
        players = build_leaderboard([e])
        self.assertTrue(all(p['rank'] == 1 for p in players))
        self.assertTrue(all(p['gameWinRate'] == 0 for p in players))

    def test_profile_decks_and_opponents(self):
        players = build_player_profiles(self.events)
        sam = next(p for p in players if p['name'] == 'Sam E')
        self.assertEqual(len(sam['decks']), 6)
        self.assertEqual(sum(deck['events'] for deck in sam['decks']), len(sam['events']))
        self.assertEqual({p['name']: sum(p['matchRecord']) for p in sam['opponents'] if sum(p['matchRecord']) == 4},
                         {'Jens H': 4, 'Josh E': 4})
        by_id = {p['id']: p for p in players}
        meetings = 0
        for player in players:
            for key in ('matchRecord', 'gameRecord'):
                self.assertEqual([sum(deck[key][i] for deck in player['decks']) for i in range(3)],
                                 player[key])
            for deck in player['decks']:
                self.assertAlmostEqual(deck['matchWinRate'], deck['matchRecord'][0] / sum(deck['matchRecord']))
                self.assertAlmostEqual(deck['gameWinRate'], deck['gameRecord'][0] / sum(deck['gameRecord']))
            for opponent in player['opponents']:
                meetings += sum(opponent['matchRecord'])
                reverse = next(p for p in by_id[opponent['id']]['opponents'] if p['id'] == player['id'])
                w, l, d = opponent['matchRecord']
                self.assertEqual(reverse['matchRecord'], [l, w, d])
                w, l, d = opponent['gameRecord']
                self.assertEqual(reverse['gameRecord'], [l, w, d])
        self.assertEqual(meetings, 63 * 2)

    def test_matchups_rank_order_and_individual_scores(self):
        players = build_player_profiles(list(reversed(self.events)))
        total = 0
        for player in players:
            self.assertEqual([p['id'] for p in player['matchups']],
                             [p['id'] for p in players])
            own = next(p for p in player['matchups'] if p['isSelf'])
            self.assertEqual(own['id'], player['id'])
            self.assertEqual(own['matches'], [])
            self.assertIn('matchup-self-label">You</span>', render_matchups(player))
            for opponent in player['matchups']:
                matches = opponent['matches']
                total += len(matches)
                self.assertEqual([m['date'] for m in matches], sorted(m['date'] for m in matches))
                if not matches:
                    continue
                summary = next(p for p in player['opponents'] if p['id'] == opponent['id'])
                self.assertEqual([
                    sum(m['wins'] > m['losses'] for m in matches),
                    sum(m['wins'] < m['losses'] for m in matches),
                    sum(m['wins'] == m['losses'] for m in matches),
                ], summary['matchRecord'])
                self.assertEqual([sum(m[key] for m in matches) for key in ('wins', 'losses', 'draws')],
                                 summary['gameRecord'])
        self.assertEqual(total, 126)  # 63 matches, both perspectives, excluding byes.

    def test_matchup_box_colors_and_details(self):
        for wins, losses, color in [(2, 1, 'win-close'), (1, 0, 'win-close'),
                                    (2, 0, 'win-sweep'), (0, 2, 'loss-sweep'),
                                    (1, 2, 'loss-close'), (0, 1, 'loss-close'),
                                    (1, 1, 'draw'), (0, 0, 'draw')]:
            with self.subTest(score=(wins, losses)):
                html = render_matchups({'matchups': [{
                    'id': 42, 'name': 'A & B', 'rank': 3,
                    'matches': [{'wins': wins, 'losses': losses, 'draws': 0,
                                 'date': '2026-11-15', 'event': 'League <final>', 'round': 2}],
                }]})
                self.assertIn(f'class="match-box {color}"', html)
                self.assertIn(f'{wins}–{losses}', html)
                self.assertIn('A &amp; B', html)
                self.assertIn('League &lt;final&gt;', html)
                self.assertIn('Round 2', html)
                self.assertIn('tabindex="0"', html)


if __name__ == '__main__':
    unittest.main()
