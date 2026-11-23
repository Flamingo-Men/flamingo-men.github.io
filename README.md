# The Flamingo Men

Website for the Flamingo Men fantasy football league (est. 2016).

- `index.html` is the built site, served by GitHub Pages.
- `src/template.html` and `src/build.py` build it: `python3 src/build.py` fills the template from `data/` and writes `index.html`.
- `data/league.json` holds trades and season stats; `data/drafts.json` holds every draft board.
- `img/` holds owner photos, cutouts and draft board photos.
- `img/nfl/` holds a photo of every NFL player on the site (ESPN headshots, and team logos for defenses), packed into sprite sheets by `python3 src/headshots.py CACHE_DIR`; `data/heads.json` says where each player is. Run it after `src/players.py` and before `src/build.py`.
