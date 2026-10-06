# Mémoire de reprise — Renault Trafic I

## Affiche, icône et aperçu — 2026-10-06

- Demande de l'utilisateur : reprendre l'esprit des posters et icônes de MilitaryDrop, MyTailorIsRich, SignalSmoke et TimberChainsaw.
- Poster créé avec le titre `RENAULT` / `TRAFIC I`, fourgon bleu marine vu de trois quarts, fond crème et accent cuivre. Icône assortie sans texte, avec fond transparent natif.
- Génération réalisée avec l'outil intégré `image_gen`. Sources, prompts et détails de préparation conservés dans `Assets/art/`, voir `Assets/art/README.md`.
- Installés : `Contents/mods/batman_RenaultTrafic1/42.21/poster.png` (1254 × 1254 RGB), `icon.png` (64 × 64 RGBA) et `preview.png` à la racine (512 × 512, 270 833 octets). Ajout de `icon=icon.png` au `42.21/mod.info` ; sauvegarde dans `Assets/art/mod.info.before_art`.
- Contrôle visuel du poster et de l'aperçu, puis de l'icône à 64 pixels sur fonds clair et sombre. Dimensions, références exactes et alpha contrôlés. Aucun essai en jeu ni publication Workshop effectué.
- Aucun fait moteur nouveau établi : la base de connaissances générique n'a pas été modifiée pour cette création graphique.

## Points de reprise précédents

- La physique, la texture propre et l'accès au stockage par la porte coulissante ont été acceptés par l'utilisateur.
- L'agrandissement des roues de 12 % et les vitres transparentes avec shader embarqué autorisé restent à confirmer en jeu après un redémarrage complet et l'apparition d'un nouveau Trafic. Ne pas déduire leur validation de la demande d'affiche.
- Les notes historiques sauvegardées se trouvent dans `Assets/backup/2026-10-06_175100_roues_vitres/REPRISE_SESSION.md` et les sauvegardes précédentes. Cette copie de sauvegarde précède l'implémentation des roues et des vitres.

## Préparation de la première publication — 2026-10-06

- Autorisation explicite de l'utilisateur : rédiger les descriptions française et anglaise, commiter, pousser et publier sur le Workshop.
- `README.steam` (anglais) et `README.steam.fr` (français) présentent le premier essai de véhicule, Blender piloté via un agent de codage et la création depuis les blueprints officiels sans modèle 3D existant. Cette provenance est déclarée par l'utilisateur ; aucune provenance supplémentaire inventée.
- `workshop.txt` synchronisé avec l'anglais, titre `Renault Trafic I T800 [B42.21]`, tags `Build 42;Vehicles;Models;WIP`, visibilité publique. Première version `0.1.0`, cohérente avec le `mod.info`.
- Simulation avec l'outil local `steam_workshop_publish.py` : aucun blocage, 22 fichiers / 2,1 Mo, anglais 2 109 octets et français 2 431 octets avant attribution de l'ID Workshop. Les outils ajoutent automatiquement les identifiants à chaque langue.
- Contrôles de structure et de métadonnées effectués ; aucun nouveau test en jeu ou en multijoueur. Le retour sur les roues et vitres demeure en attente.
- Création du dépôt Git nécessaire : le projet n'en possédait pas. Sources Blender et outils inclus ; sauvegardes, diagnostics, fichiers temporaires et rendus intermédiaires exclus par `.gitignore`.
