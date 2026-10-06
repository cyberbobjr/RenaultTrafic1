# Renault Trafic I T800 — Project Zomboid 42.21

Premier essai de véhicule pour Project Zomboid, réalisé en pilotant Blender via un agent de codage. Modèle construit à partir des blueprints officiels du véhicule, sans modèle 3D préexistant.

Fourgon tôlé de 1985, empattement court et toit bas, deux places avant, stockage de 120 accessible à l'arrière et par la porte coulissante. Peinture blanche ou bleue, intérieur modélisé, portes et capot animés.

## Contenu du dépôt

- `Contents/mods/batman_RenaultTrafic1/` : mod à charger, ressources dans `common`, scripts et Lua dans `42.21`.
- `Assets/RenaultTraficI.blend` : scène de travail actuelle.
- `Assets/tools/` : construction, texture, aperçu et export Blender/FBX.
- `Assets/art/` : sources du poster et de l'icône, prompts et préparation.
- `README.steam` et `README.steam.fr` : descriptions anglaise et française.
- `docs/REPRISE_SESSION.md` : mémoire de travail et limites de validation.

Les sauvegardes locales, anciens fichiers Blender, diagnostics et rendus intermédiaires sont exclus du dépôt. Aucun autre mod n'est requis.

## Développement

Le jeu charge directement `Contents/mods` depuis le projet placé dans `Zomboid/Workshop`. Activer `batman_RenaultTrafic1` dans le sélecteur de mods.

Après modification d'un script de véhicule ou d'un shader, quitter complètement le jeu, le relancer et créer un nouveau véhicule pour l'essai. Les anciens véhicules conservent leur couleur et leur état.

Les essais en jeu sont réalisés par l'utilisateur. Les contrôles statiques et rendus Blender ne constituent pas une validation en jeu ou en multijoueur.
