# Fischer price watch

Sleduje cenu zajazdu [VOI Baia di Tindari](https://www.fischer.cz/italie/sicilie/voi-baia-di-tindari-resort)
na Fischer.cz kazdych 20 minut cez GitHub Actions a pri zlacneni posle push
notifikaciu cez [ntfy](https://ntfy.sh).

## Ako to funguje

1. GitHub Actions spusti `check_price.py` kazdych 20 minut.
2. Skript nacita stranku cez Playwright (headless Chromium) a najde aktualnu cenu najblizsieho terminu.
3. Porovna ju s najnizsou doteraz zaznamenanou cenou v `price.json`.
4. Ak cena klesla, posle notifikaciu na ntfy topic (secret `NTFY_TOPIC`).
5. Historiu cien uklada do `price.json` (commituje spat do repa).

## Nastavenie

- Secret `NTFY_TOPIC` v Settings -> Secrets and variables -> Actions.
- V mobilnej appke ntfy prihlasit rovnaky topic.
- Vypnutie: Actions -> Fischer price watch -> "..." -> Disable workflow.

Pozn.: GitHub automaticky vypne scheduled workflow po 60 dnoch bez aktivity v repe.
