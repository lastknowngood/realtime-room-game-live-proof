# AGENTS

## Zweck

Diese Datei ist die kleine Repo-Oberflaeche fuer ein separates Projekt-Repo.
Host-Betrieb, Firewall, SSH, globale Backups und Browser-Tooling bleiben im
Host-Repo.

## Erst lesen

1. `README.md`
2. `ops/deploy-contract.v1.yaml`

## Wahrheitsquellen

- `README.md`
  - aktueller Projektzustand, lokaler QA-Pfad und kurze Proof-Zusammenfassung
- `ops/deploy-contract.v1.yaml`
  - gewuenschter Normalzustand plus `notes` fuer Steady-State und Proof-Hinweise

## Harte Regeln

- keine Secrets, Tokens, Keys oder Browserdaten in Git
- `README.md` und `ops/deploy-contract.v1.yaml` im selben Arbeitsblock
  nachziehen, wenn sich der reale Proof- oder Steady-State aendert
- Host-Runbooks nicht in dieses Repo kopieren
- bei intentionalen verhaltensaendernden Defektfixes:
  - Failure erst belegen
  - den kleinsten faithful projekt-lokalen Regression-Check waehlen
  - danach den repo-lokalen Closeout-Pfad schliessen

## Klarheitsregeln

- `lifecycle.mode: live` ist die Contract-/Proof-Klasse, nicht automatisch ein
  Claim fuer retained Runtime, retained DNS oder retained Host-Ressourcen.
- Der aktuelle Zustand muss in `README.md` unter `## Aktueller Zustand` und in
  den `notes` des Deploy-Contracts stehen.
- Host-Evidence wird nur als Pfad ins Host-Repo referenziert; Host-Runbooks
  werden nicht kopiert.

## Pflicht-Gates vor "fertig" oder "clean"

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File tools/repo/check-project-closeout.ps1
git status --short --ignored
```

## README-Mindestform

- `## Charakter`
- `## Aktueller Zustand`
- `## Lokale Entwicklung`
- `## Laufzeitverhalten`
- entweder `## Proof-Status` oder `## Reale Evidence`
