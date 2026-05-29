# Suivi de developpement
## Auteur:
**Toussaint Guillaume**
## Le 21/05/2026

## Partie PP:
### Prochaines actions:
- Gestion des changements d'outils:
    - Supprimer les tooltype du json machine (pour se baser sur l'apt uniquement).
    - Lors de la lecture d'un LOADTL: recuperer le numéro et le type de l'outil et ajouter une var de passage boolean (car on ne veut rien emettre lors de sa lecture).
    - Lors de la lecture d'un SPINDL_NAME: on recupere le numéro de broche uniquement (pas d'emission).
    - Lors de la lecture d'un SPINDL: on suit le plan defini sur l'Excel et on remet la var de passage sur False.
- Gestion des synchronisations des canaux.
### Actions futures:
- Creer un HTML pour l'affichage des configurations machines. Structurer avec JSON pour l'interpretation des parametres du JSON machine et leurs valeurs.
- Creer un HTML pour la generation des gammes avec vue des trajectoires en 3D, etc...
### Points a verifier (dans app):
- Faire une verification des arrets de broche en cas de passage tournage -> fraisage.
### Points a verifier (dans CATIA):
### Ameliorations a prevoir:
- Gestion des spindle on/off: cable avec on/off a chaque changement d'outil. Voir pour mettre plus d'intelligence a ce niveau (pas de on/off si meme broche, etc...).
### Choses a noter dans la doc finale:
- Pas de prise en compte des correcteurs en tournage mais en fraisage uniquement.
- Inversion des coordonnees X/Y basee sur les booleens outil xmirror et ymirror.
- Pour les machines ayant un peigne monobloc en broche principale (type B075), il faut programmer dans CATIA tous les outils du meme cote (repere canal 1). L'inversion des coordonnees X se fait par le PP.
- Un degagement d'outil en X est ecrit en dur avant les changements d'outil (T0 G0 X...) sans prise en compte de l'axe C courant (le degagement en X sera le meme si C=0 ou C=45). La valeur du X est donne par le hometool X.
- Les outils positionnes avec un vecteur K[0, 1, 0] ne sont pas pris en compte.
- 

## Partie analyse:
### Prochaines actions:
### Actions futures:
### Points a verifier (dans app):
### Points a verifier (dans CATIA):
### Ameliorations a prevoir:
### Choses a noter dans la doc finale:
- Les infos de l'analyse sont donnees avec X au rayon dans tous les cas (meme si true ou false dans JSON).

## Partie viewer:
### Prochaines actions:
### Actions futures:
### Points a verifier (dans app):
### Points a verifier (dans CATIA):
### Ameliorations a prevoir:
### Choses a noter dans la doc finale:
- Les coordonnees affichees sont toujours au rayon.
- Les hometool sont appliques par le simulateur pour determiner le 1er point de la trajectoire de l'outil courant.