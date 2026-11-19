"""Cache Scryfall metadata and card images for the offline card cloud."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen

from analyze_league import analyze, card_stats

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data/scryfall-cards.json'
HEADERS = {'User-Agent': 'PauperUnwrapped/1.0 (local league recap)',
           'Accept': 'application/json'}


def image_metadata(card):
    """Use the front image for cards with separate face images."""
    images = card.get('image_uris') or card.get('card_faces', [{}])[0].get('image_uris', {})
    return {'id': card['id'], 'image': f"assets/cards/{card['id']}.jpg",
            'source': images['normal'], 'scryfall': card['scryfall_uri']}


def resolve_batch(names):
    request = Request('https://api.scryfall.com/cards/collection',
                      data=json.dumps({'identifiers': [{'name': name} for name in names]}).encode(),
                      headers=HEADERS | {'Content-Type': 'application/json'})
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get('not_found'):
        raise ValueError(f"Scryfall could not resolve: {result['not_found']}")
    by_name = {}
    for card in result['data']:
        for name in [card['name'], *(face['name'] for face in card.get('card_faces', []))]:
            by_name[name.casefold()] = card
    return {name: image_metadata(by_name[name.casefold()]) for name in names}


def download_image(metadata):
    path = ROOT / metadata['image']
    if path.is_file():
        return
    request = Request(metadata['source'], headers=HEADERS | {'Accept': 'image/jpeg'})
    with urlopen(request, timeout=30) as response:
        content = response.read()
    if not content.startswith(b'\xff\xd8\xff'):
        raise ValueError(f"Expected a JPEG image from {metadata['source']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.part')
    temporary.write_bytes(content)
    temporary.replace(path)


def main():
    tournaments = json.loads((ROOT / 'data/tournaments.json').read_text())
    entries = analyze(tournaments, ROOT / 'data/moxfield-exports')['decklists']
    names = [row['card'] for row in card_stats(entries, include_basics=True)]
    cache = json.loads(CACHE.read_text()) if CACHE.is_file() else {}
    missing = [name for name in names if name not in cache]
    for start in range(0, len(missing), 75):
        cache.update(resolve_batch(missing[start:start + 75]))
        CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False) + '\n')
        # Keep collection lookups well below the API request limit.
        time.sleep(.6)
    # Images use Scryfall's separate image CDN. Limit concurrency and cache locally.
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(download_image, {cache[name]['id']: cache[name] for name in names}.values()))
    print(f'Cached Scryfall images for all {len(names)} league cards.')


if __name__ == '__main__':
    main()
