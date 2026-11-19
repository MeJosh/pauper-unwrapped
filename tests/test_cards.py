"""Verify card popularity counting and decklist coverage."""

import copy
from collections import Counter
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from analyze_league import analyze, card_stats
from fetch_card_images import image_metadata
from build_leaderboard import build_player_card_data
from leaderboard import build_player_profiles


class CardPopularityTests(unittest.TestCase):
    def setUp(self):
        self.events = json.loads((ROOT / 'data/tournaments.json').read_text())
        self.exports = ROOT / 'data/moxfield-exports'

    def test_combined_boards_deduplicate_decks_but_add_copies(self):
        entries = [
            {'mainboard': {'Shared': 3, 'Forest': 20}, 'sideboard': {'Shared': 1}},
            {'mainboard': {}, 'sideboard': {'Shared': 2, 'Side only': 1}},
        ]
        combined = card_stats(entries)
        self.assertEqual(combined, [{'card': 'Shared', 'decks': 2, 'copies': 6},
                                    {'card': 'Side only', 'decks': 1, 'copies': 1}])
        self.assertEqual(card_stats(entries, 'mainboard'),
                         [{'card': 'Shared', 'decks': 1, 'copies': 3}])
        self.assertIn({'card': 'Forest', 'decks': 1, 'copies': 20},
                      card_stats(entries, include_basics=True))
        self.assertEqual(card_stats([]), [])

    def test_scryfall_normal_and_double_faced_images(self):
        card = {'id': 'example-id', 'scryfall_uri': 'https://scryfall.com/card/example',
                'image_uris': {'normal': 'https://cards.scryfall.io/normal/example.jpg'}}
        self.assertEqual(image_metadata(card)['source'], card['image_uris']['normal'])
        images = card.pop('image_uris')
        card['card_faces'] = [{'image_uris': images},
                              {'image_uris': {'normal': 'https://cards.scryfall.io/normal/back.jpg'}}]
        metadata = image_metadata(card)
        self.assertEqual(metadata['source'], images['normal'])
        self.assertEqual(metadata['image'], 'assets/cards/example-id.jpg')

    def test_source_totals_and_board_rankings(self):
        result = analyze(self.events, self.exports)
        self.assertEqual(result['coverage'], {'entries': 46, 'captured': 46, 'missing': []})
        self.assertEqual(result['allCards'][0], {'card': 'Nihil Spellbomb', 'decks': 18, 'copies': 46})
        self.assertEqual(result['mainboardCards'][0], {'card': 'Malevolent Rumble', 'decks': 14, 'copies': 56})
        self.assertEqual(result['sideboardCards'][0], {'card': 'Breath Weapon', 'decks': 16, 'copies': 37})
        for board, key in [(None, 'allCards'), ('mainboard', 'mainboardCards'), ('sideboard', 'sideboardCards')]:
            for row in result[key]:
                lists = [e for e in result['decklists'] if row['card'] in
                         (set(e['mainboard']) | set(e['sideboard']) if board is None else e[board])]
                self.assertEqual(row['decks'], len(lists))

    def test_player_card_totals_partition_league_counts(self):
        analysis = analyze(self.events, self.exports)
        images = json.loads((ROOT / 'data/scryfall-cards.json').read_text())
        player_data = [build_player_card_data(p, analysis, images)
                       for p in build_player_profiles(self.events)]
        self.assertEqual(sum(p['coverage']['captured'] for p in player_data), 46)
        for board in ['all', 'mainboard', 'sideboard']:
            copies, decks = Counter(), Counter()
            for player in player_data:
                for row in player['boards'][board]:
                    copies[row['card']] += row['copies']
                    decks[row['card']] += row['decks']
            source = card_stats(analysis['decklists'], None if board == 'all' else board, True)
            self.assertEqual(copies, Counter({r['card']: r['copies'] for r in source}))
            self.assertEqual(decks, Counter({r['card']: r['decks'] for r in source}))
        for player in player_data:
            names = {r['card'] for r in player['boards']['all']}
            self.assertEqual(set(player['images']), names)
            for metadata in player['images'].values():
                self.assertTrue((ROOT / 'players' / metadata['image']).is_file())

    def test_player_cloud_excludes_other_players_and_tracks_missing_lists(self):
        entries = [
            {'competitorId': 1, 'mainboard': {'Shared': 4}, 'sideboard': {'Shared': 1}},
            {'competitorId': 2, 'mainboard': {'Other player only': 4}, 'sideboard': {}},
        ]
        analysis = {'decklists': entries, 'coverage': {'missing': [{'competitorId': 1}]}}
        data = build_player_card_data({'id': 1, 'events': [{}, {}]}, analysis, {})
        self.assertEqual(data['boards']['all'], [{'card': 'Shared', 'decks': 1, 'copies': 5}])
        self.assertEqual(data['coverage'], {'entries': 2, 'captured': 1,
                                           'missing': [{'competitorId': 1}]})
        empty = build_player_card_data({'id': 3, 'events': []}, analysis, {})
        self.assertEqual(empty['boards']['all'], [])

    def test_missing_lists_and_incomplete_events(self):
        events = copy.deepcopy(self.events)
        events[0]['status'] = 'IN_PROGRESS'
        with tempfile.TemporaryDirectory() as exports:
            result = analyze(events, Path(exports))
        expected = sum(len(e['standings']) for e in events if e['status'] == 'COMPLETE')
        self.assertEqual(result['coverage']['entries'], expected)
        self.assertEqual(len(result['coverage']['missing']), expected)
        self.assertEqual(result['coverage']['captured'], 0)
        self.assertEqual(len(result['events']), 5)
        self.assertEqual(result['allCards'], [])


if __name__ == '__main__':
    unittest.main()
