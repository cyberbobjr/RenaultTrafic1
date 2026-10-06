# Modèle de présentation pour Sketchfab

## Fichiers à importer

- **`RenaultTraficI_blue.glb`** : version bleue, conseillée pour la page Workshop, assortie au poster ; 670 604 octets.
- `RenaultTraficI_white.glb` : variante blanche ; 564 096 octets.

Chaque GLB contient le fourgon entier (16 instances de maillages, 4 944 triangles), avec trois textures PNG embarquées. Importer un seul GLB par modèle Sketchfab ; aucun ZIP ni fichier de texture séparé n'est nécessaire.

Présentation statique, portes fermées. Roues agrandies de 12 % comme dans le mod, intérieur conservé et vitres transparentes. Matériaux PBR adaptés au web : leur éclairage ne reproduit pas les shaders de Project Zomboid. Les animations du jeu ne sont pas incluses dans cet export de présentation.

`preview_blue.png` et `preview_white.png` sont des rendus Blender de ces matériaux, pas des captures du jeu ou de Sketchfab.

## Envoi et intégration Steam

1. Se connecter à Sketchfab et choisir Upload.
2. Importer `RenaultTraficI_blue.glb`, avec le titre **Renault Trafic I T800 — Project Zomboid**.
3. Régler l'éclairage et la vue initiale de trois quarts avant, puis publier le modèle.
4. Copier le lien de sa page Sketchfab.
5. Sur la [page Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3814732564), ouvrir la gestion des captures et vidéos, puis ajouter ce lien dans le champ Sketchfab.

Le lien Sketchfab n'existe qu'après hébergement. Cet export local ne crée pas de modèle en ligne.

Sources officielles : [formats et recommandations Sketchfab](https://sketchfab.com/developers/guidelines), [intégration Steam](https://help.steampowered.com/en/faqs/view/51D3-5714-53CA-2886).

## Description proposée

**FR :** Renault Trafic I T800 de 1985, empattement court, toit bas et fourgon tôlé. Mon premier essai de véhicule pour Project Zomboid Build 42.21, créé en pilotant Blender via un agent de codage à partir des blueprints officiels, sans modèle 3D préexistant. Aperçu du véhicule du mod : https://steamcommunity.com/sharedfiles/filedetails/?id=3814732564

**EN:** 1985 Renault Trafic I T800, short wheelbase, low roof and panel cargo body. My first vehicle experiment for Project Zomboid Build 42.21, created by controlling Blender through a coding agent from official vehicle blueprints, without using an existing 3D model. Preview of the mod vehicle: https://steamcommunity.com/sharedfiles/filedetails/?id=3814732564

## Reproduction

Préparer les textures avec Python système : `python Assets/tools/trafic_sketchfab_textures.py` (Pillow et NumPy). Dans Blender, avec la scène actuelle ouverte :

```python
exec(open(r'C:\Users\cyber\Zomboid\Workshop\RenaultTrafic1\Assets\tools\trafic_sketchfab_export.py', encoding='utf-8').read())
```

L'export utilise des copies isolées des collections `EXPORT_trafic` et `TRF_wheels`, sans modifier leurs géométries, UV, matériaux ou transformations. Aucune sauvegarde du `.blend` source ni écriture dans `Contents`.

Contrôles statiques : en-têtes GLB 2.0, longueurs, 16 maillages, trois textures embarquées sans chemin externe, vitre en `alphaMode = BLEND`, carrosserie/roues opaques et absence de caméra/éclairage/animation dans les GLB. Empreintes de la géométrie source avant/après identiques ; empreintes des 22 fichiers du mod et du `.blend` sauvegardé inchangées. Export et rendu réalisés dans Blender 5.2.2 LTS. La visionneuse Sketchfab reste à confirmer après téléversement.
