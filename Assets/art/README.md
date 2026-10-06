# Affiche et icône — Renault Trafic I

Créées le 6 octobre 2026 avec l'outil intégré `image_gen`, à partir des références locales. Aucune publication Workshop effectuée.

## Direction visuelle

- Références : posters et icônes de MilitaryDrop, MyTailorIsRich, SignalSmoke et TimberChainsaw, dans leurs variantes `42.21`.
- Référence du véhicule : `../build/trafic_texture_blue.png` (rendu de travail, pas une capture du jeu).
- Titre : **RENAULT** / **TRAFIC I**.
- Fourgon bleu marine, vu de trois quarts avant, toit bas et soute tôlée ; fond crème, contours nets et accent cuivre.
- Palette demandée : crème `#FEF6E1`, marine `#07233C`, cuivre `#D66B3D`.

## Sources conservées

- [Poster original](poster_source.png) et [prompt du poster](poster_prompt.txt).
- [Icône originale avec alpha natif](icon_source.png) et [prompt de l'icône](icon_prompt.txt).
- [Contrôle visuel de l'icône](icon_check.png), à taille réelle et agrandie, sur fond clair et sombre.
- `mod.info.before_art` : métadonnées avant ajout de `icon=icon.png`.

## Fichiers installés

| Fichier | Format | Taille |
|---|---|---|
| `../../Contents/mods/batman_RenaultTrafic1/42.21/poster.png` | RGB, 1254 × 1254 | 1 171 534 octets |
| `../../Contents/mods/batman_RenaultTrafic1/42.21/icon.png` | RGBA, 64 × 64, transparent | 5 660 octets |
| `../../preview.png` | RGB, 512 × 512 | 270 833 octets |

Les références `poster=poster.png` et `icon=icon.png` du `mod.info` correspondent exactement aux noms installés.

Le poster et l'aperçu sont préparés avec le script `finalize_art.py poster` de la compétence `pz-workshop-art`. L'icône est préparée avec `../tools/trafic_finalize_icon.py` : recadrage selon l'alpha, réduction à 60 pixels maximum et centrage dans un carré de 64 pixels. L'alpha natif est conservé, sans détourage par couleur.

Contrôles effectués : orthographe du titre, lisibilité de l'aperçu, dimensions, modes RGB/RGBA, transparence des coins et lisibilité de l'icône sur deux fonds. Aucun essai du sélecteur de mods en jeu effectué par l'agent.
