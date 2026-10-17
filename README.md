# ADN for Kodi

Unofficial Kodi add-on for [ADN (Animation Digital Network)](https://animationdigitalnetwork.com),
the French streaming platform for Japanese animation.

> [!IMPORTANT]
> This add-on is not developed, supported or endorsed by ADN. An active ADN subscription is
> required to watch videos.

## Features

- Sign in with your ADN account, email verification code included, and pick a profile
- Resume, My list, For you, Catalogue (the rails of the ADN home page) and Search
- Series and season pages; from Resume and My list, "Go to series" and "Go to season" context
  menus
- Add to and remove from My list
- Playback in VOSTFR (original with subtitles) or VF (French dub), in the chosen quality
- Resumes where ADN saved your position
- Progress sent to ADN while you watch: an episode started in Kodi resumes on your other devices,
  and the other way round
- Season episodes played in a row (next and previous in the Kodi playlist)
- Menus in French or English

The add-on downloads nothing and bypasses no geographic restriction: it streams the video while you
watch.

## Requirements

- Kodi 20 or later (tested on Kodi 21.2 on Windows)
- An active ADN subscription
- `script.module.requests`, installed automatically by Kodi from its official repository

## Installation

Everything is on [centulus.github.io/kodi-repo-centulus](https://centulus.github.io/kodi-repo-centulus/).
First, in Kodi: Settings > System > Add-ons, enable "Unknown sources".

**From the Centulus repository** (recommended: Kodi keeps the add-on up to date)

1. Settings > File manager > Add source: enter `https://centulus.github.io/kodi-repo-centulus/`
   and name it `centulus`.
2. Settings > Add-ons > Install from zip file > `centulus` > `repository.centulus-1.0.0.zip`.
3. Settings > Add-ons > Install from repository > Centulus Repository > Video add-ons > ADN.

**From the add-on zip** (no automatic updates): download the ADN zip from the same page, then
Settings > Add-ons > Install from zip file.

**From this repository**: zip it yourself (the folder inside must be named `plugin.video.adn`),
then Install from zip file.

```sh
git archive --format=zip --prefix=plugin.video.adn/ -o plugin.video.adn.zip HEAD
```

## First use

Open any menu that needs an account (Resume, for instance): the add-on asks for your email or
username, then your password, then the code sent by email if your account requires one. With
several profiles, it asks which one to use. "Change profile" and "Sign out" are at the bottom of
the main menu.

## Settings

| Setting | Default | What it does |
|---|---|---|
| Default language | Follow ADN profile | VOSTFR, VF, or the language saved on your ADN profile |
| Default quality | Follow ADN profile | Auto, 1080p, 720p or 480p. Following the profile means Auto, or the profile's quality when its "Consommation responsable" mode is on. When a quality is missing for a video, the closest one plays |
| Menu language | Français | Français or English, whatever Kodi's language |

## Privacy

- Your password is never saved: it is used once, to sign in. ADN's tokens then keep the session
  alive; they are stored in the add-on settings on your device.
- The add-on only talks to ADN's servers and sends no statistics anywhere else.
- "Sign out" ends the session on ADN's side and clears the tokens and the profile.

## Development

```sh
python -m venv .venv
.venv/Scripts/python -m pip install pytest requests ruff   # .venv/bin/ on Linux and macOS
.venv/Scripts/python -m pytest
.venv/Scripts/ruff check .
```

The code lives in `resources/lib/`:

- `adn/`: ADN API client, with no dependency on Kodi;
- `kodi/`: settings, translations, list items, dialogs;
- `routes/`: one function per add-on action;
- `player/`: playback, season playlist, progress reports.

The code targets Python 3.8, the version some Kodi builds embed.

## License

Copyright (c) 2026 Centulus. Code under the [MIT license](LICENSE.txt).

Bundled libraries in `resources/lib/vendor/`, each with its own license:
[rsa](https://github.com/sybrenstuvel/python-rsa) (Apache-2.0),
[pyasn1](https://github.com/pyasn1/pyasn1) (BSD-2-Clause) and
[pyaes](https://github.com/ricmoo/pyaes) (MIT).

## Trademarks

ADN, Animation Digital Network and the ADN logo (used as the add-on icon) are trademarks and works
of Animation Digital Network. They are used here only to name the service the add-on gives access
to. The videos, images and texts shown belong to their respective owners.
