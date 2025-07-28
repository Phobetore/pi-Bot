# pi-Bot

pi-Bot est un bot Discord permettant de gérer facilement des lancers de dés, avec de nombreuses options de personnalisation. Basé sur [Py‑Cord](https://docs.pycord.dev/), il propose un système multilingue et plusieurs commandes pour simplifier la vie des joueurs comme des maîtres du jeu.

## Fonctionnalités principales

- **Lancer de dés flexible** : expressions du type `2d6+3` avec support des modificateurs et d'un nom de cible optionnel.
- **Couleurs personnalisées** : chaque utilisateur peut choisir la couleur des messages du bot (`!setcolor rouge`).
- **Préfixe configurable** : adaptation du préfixe de commande par serveur (`!setprefix ?`).
- **Jet par défaut** : possibilité de définir un lancer par défaut utilisé lorsque aucune expression n'est fournie (`!defaultRoll 1d20`).
- **Support multilingue** : anglais, français, allemand et espagnol via la commande `!setlang`.
- **Sauvegarde automatique** : préférences et statistiques stockées dans des fichiers JSON et mises en cache en mémoire.

## Installation

1. Clonez ce dépôt.
2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
3. Créez un fichier `config.json` avec le contenu suivant :
   ```json
   {
       "token": "VOTRE_TOKEN_DISCORD",
       "prefix": "!"
   }
   ```
4. Lancez le bot :
   ```bash
   python main.py
   ```

## Guide rapide

### Pour les joueurs et MJ

- **Lancer un dé simple** : `!roll 1d20`
- **Ajouter des modificateurs** : `!roll 1d20+5` ou `!r 1d6+1d4-2`
- **Raccourci** : `!r` est équivalent à `!roll`
- **Jet par défaut** : si un jet est configuré via `!defaultRoll`, `!r` sans argument utilisera ce jet
- **Changer la couleur des messages** : `!setcolor rouge`
- **Voir la couleur actuelle** : `!getcolor`

### Pour les modérateurs

- **Changer la langue** : `!setlang fr`
- **Définir un jet par défaut** : `!defaultRoll 1d20+5`
- **Modifier le préfixe** : `!setprefix ?`

Seules les personnes ayant la permission « Manage Server » peuvent modifier la langue, le jet par défaut ou le préfixe.

## Notes supplémentaires

- Les fichiers `user_stats.json`, `user_preferences.json` et `server_preferences.json` sont générés automatiquement et ignorés par git.
- Les journaux d'audit sont enregistrés dans `audit.log`.

## Contribuer

Les contributions sont bienvenues ! N'hésitez pas à ouvrir une *issue* ou une *pull request* pour proposer des améliorations.

