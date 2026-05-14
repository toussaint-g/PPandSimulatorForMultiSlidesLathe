# Suivi de developpement
## Auteur:
**Toussaint Guillaume**
## Le 08/05/2026

## Partie PP:
### Points traites:
- CIRCLE -> OK.
- CYLNDR -> OK.
- Canal 1 uniquement teste !!
### Prochaines actions:
- Gestion HELICAL a implementer.
- Gestion des orientations d'outils pour la generations des rotations C.
- Revoir la gestion des hometool (GOTO avant changement d'outil).
- Gestion de tous les canaux.
### Points a verifier (dans app):
- Les arret de broche: rotation permanente en tournage et arret a chaque outil en fraisage. Voir aussi lors du chargement du 1er outil (-> pas de M5 avant l'appel du 1er outil dans le prog).
- Pas d'arret de broche en cas de passage tournage -> fraisage.
- Faire une verification de coherence des home_tool_x. Pas mal de modifications faites et pas les datas pour faire toutes les verification appropriees (commit **x_diameter update**).
### Points a verifier (dans CATIA):
### Ameliorations a prevoir:
- Gestion des spindle on/off: cable avec on/off a chaque changement d'outil. Voir pour mettre plus d'intelligence a ce niveau (pas de on/off si meme broche, etc...).
### Choses a noter dans la doc finale:
- Pas de prise en compte des correcteurs en tournage mais en fraisage uniquement.
- Inversion des coordonnees X/Y basee sur les booleens outil xmirror et ymirror.
- Pour les machines ayant un peigne monobloc en broche principale (type B075), il faut programmer dans CATIA tous les outils du meme cote (repere canal 1). L'inversion des coordonnees X se fait par le PP.

## Partie analyse:
### Points traites:
### Prochaines actions:
### Points a verifier (dans app):
### Points a verifier (dans CATIA):
### Ameliorations a prevoir:
### Choses a noter dans la doc finale:
- Les infos de l'analyse sont donnees avec X au rayon dans tous les cas (meme si true ou false dans JSON).

## Partie viewer:
### Points traites:
### Prochaines actions:
- Gerer les rotations et les sens du C en fraisage (avec ajout d'interpolations).
- Ajouter une couleur (ex violet) pour les mouvements C.
### Points a verifier (dans app):
- Inversion des X suivant les differents canaux.
### Points a verifier (dans CATIA):
### Ameliorations a prevoir:
### Choses a noter dans la doc finale:
- Les cordonnees affichees sont toujours au rayon (a confirmer car pas sur).
- 
