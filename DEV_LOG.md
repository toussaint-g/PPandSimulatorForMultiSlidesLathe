# Suivi de developpement
## Auteur:
**Toussaint Guillaume**
## Le 21/05/2026

## Partie PP:
### Prochaines actions:
- Gestion des synchronisations des canaux.
- Regenerer le fichier linear_3x_PATH1.aptsource depuis CATIA.
- Revoir la partie apply_tool_update dans le writer car genere des C0 avant les C... Mauvaise reaction car si pas de changement d'outil, doit continuer sans remettre le C0.
- Finaliser la partie caxis_move du writer et l'appel depuis le handler.
- Reprendre tous les messages d'erreur (CatiaConfigError, MachineConfigError, etc...) pour les rationnaliser.
### Actions futures:
- Separer toutes les briques (generateur, analyseur, simulateur)??
- Creer un HTML pour l'affichage des configurations machines. Structurer avec JSON pour l'interpretation des parametres du JSON machine et leurs valeurs.
- Creer un HTML pour la generation des gammes avec vue des trajectoires en 3D, etc...
### Points a verifier (dans app):
- Verifier le ROTABL.
### Points a verifier (dans CATIA):
### Ameliorations a prevoir:
- Gestion des spindle on/off: cable avec on/off a chaque changement d'outil. Voir pour mettre plus d'intelligence a ce niveau (pas de on/off si meme broche, etc...).
### Choses a noter dans la doc finale:
- Pas de prise en compte des correcteurs en tournage mais en fraisage uniquement.
- Inversion des coordonnees X/Y basee sur les booleens outil xmirror et ymirror.
- Pour les machines ayant un peigne monobloc en broche principale (type B075), il faut programmer dans CATIA tous les outils du meme cote (repere canal 1). L'inversion des coordonnees X se fait par le PP.
- Un degagement d'outil en X est ecrit en dur avant les changements d'outil (T0 G0 X...) sans prise en compte de l'axe C courant (le degagement en X sera le meme si C=0 ou C=45). La valeur du X est donne par le hometool X.
- Les outils positionnes avec un vecteur K[0, 1, 0] ne sont pas pris en compte.
- ROTABL utilisable en axe C et avec des outils de type MILL frontaux uniquement. Si un autre axe ou un autre type d'outil sont selectionnes, emission d'un message d'erreur.
- Listofspindles du json machine doit refleter les différentes broches definies dans CATIA.

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