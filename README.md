# PPandSimulatorForMultiSlidesLathe

## Auteur:
**Toussaint Guillaume**

## Description:
Ce developpement a pour objectifs:
- De fournir une application capable de **generer du code ISO depuis les fichiers APT de CATIA V5**.
- D'**analyser les temps d'usinage et les distances parcourues** par chaque outil.
- De **simuler du code ISO** avec une representation 3D (STL) de la piece et des trajectoires des outils sous forme filaire.

Les machines cibles de ce projet sont des **decolleteuses CNC multi-canaux TSUGAMI avec commande FANUC**.

## Manipulateur du viewer 3D:
Differentes touches permettent d'executer des fonctions specifiques:
- **Space**  pour masquer/afficher la piece.
- **Escape**  pour masquer/afficher toutes les trajectoires.
- **Left** et **Rigth** pour faire defiler les trajectoires par outil.
- **Up** et **Down**  defilement des trajectoires en rapide et en travail par outil.

## Tests:
Pour tester l'application, vous pouvez utilier les fichiers presents dans le repertoire "data_testing". Toutes les donnees de ce dossier ont ete utilisees principalement pour le developpement de cette app.

## Generation des fichiers APT depuis CATIA V5:
- Utiliser la licence **MLG** de CATIA V5 pour la gestion des multi-canaux.
- Ne generer **qu'un fichier APT par canal** (programme).
- Positionner le **repere d'usinage de la broche principale** selon le canal 1 de la machine.
- Positionner le **repere d'usinage de la broche de reprise** selon le canal correspondant.
- Ne pas mettre de numero d'outil dans les **TPRINT**: ils sont forces par le PP en debut de commentaire.

## Mots PP pris en charge:
- CHANNEL.
- SPINDL.
- FEDRAT.
- RAPID.
- GOTO.
- INDIRV.
- TLON.
- END.
- PART_OPE.
- PROGRAM.
- MACHINE.
- CATPROCESS.
- CATPRODUCT.
- OP_NAME.
- PPRINT.
- INSERT.
- TPRINT.
- TDATA.
- LOADTL.

## Parametrage des fichiers JSON:

### tool_path_config.json:
Pour le parametrage du rendu visuel des trajectoires outils. Plusieurs options de parametrage sont possible au niveau **viewer** et **toolpath**.
#### Informations sur le parametrage:

### machines_config.json:
Pour le parametrage des machines d'usinage. Un nombre d'options sont parametrables comme les **codes M et G**, les dispositions d'outils, etc...
#### Informations sur le parametrage:
- **ipartvector**: vecteur I de la piece.
- **xmirror / ymirror**: booleens definis par outil. Si **xmirror** vaut true, les coordonnees X sont inversees dans le rendu toolpath. Si **ymirror** vaut true, les coordonnees Y sont inversees.
- **toolvector**: repere determinant les orientations des outils de fraisage dans la machine.
- **workplane**: repere determinant les plans de travail de chaque outil. Valeurs negatives pas utiles car plan de travail uniquement. /!\ Attention: les plans de travail pour les deplacements circulaires sont donnees uniquement par ces workplanes! Non prise en compte des G17/G18/G19 donnees par les programmes.
- **tooltype**: 
    - **tool_type: "TURN"** -> outil de tournage.
	- **tool_type: "MILL"** -> outil de fraisage.
- **hometool X** doit-etre renseigne au rayon et doit-etre place par rapport au ipartvector.
