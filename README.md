# pi-Bot

Un bot Discord pour gérer les jets de dés en jeu de rôle, développé avec [Py-Cord](https://docs.pycord.dev/). Le code est structuré de manière modulaire et met l'accent sur la performance et la maintenabilité.

> **Note :** Ce projet est avant tout une vitrine de mes compétences en développement. Il n'est pas conçu pour être forké massivement, mais reste ouvert aux contributions si vous souhaitez y participer.

## À propos

pi-Bot gère les jets de dés avec pas mal d'options de personnalisation. Le support multilingue et le système de cache permettent une utilisation fluide, que ce soit pour les joueurs ou les maîtres de jeu.

### Fonctionnalités

- **Jets de dés flexibles** : Expressions type `2d6+3`, `1d20+5-2`, avec multiples dés et modificateurs
- **Personnalisation des couleurs** : Chaque utilisateur peut choisir sa couleur préférée
- **Support multilingue** : Français, anglais, allemand et espagnol
- **Préfixe configurable** : Adaptation par serveur
- **Jet par défaut** : Possibilité de définir un jet par défaut par serveur
- **Cache en mémoire** : Optimisation des accès disque via un système de cache
- **Statistiques** : Compteur de jets de dés par utilisateur
- **Logs d'audit** : Traçabilité des actions importantes

## Architecture technique

### Structure du projet

```
pi-Bot/
├── main.py                    # Point d'entrée, configuration, commandes serveur
├── cogs/
│   └── dice_rolls.py         # Cog principal : logique des jets de dés
├── requirements.txt          # Dépendances Python
├── config.json              # Configuration (token, préfixe) - NON VERSIONNÉ
├── user_preferences.json    # Préférences utilisateurs - NON VERSIONNÉ
├── user_stats.json         # Statistiques utilisateurs - NON VERSIONNÉ
├── server_preferences.json # Préférences serveurs - NON VERSIONNÉ
└── audit.log              # Logs d'audit - NON VERSIONNÉ
```

### Composants clés

#### Système de cache (CACHE)

Le cache en mémoire utilise des verrous asynchrones (`asyncio.Lock`) pour garantir la cohérence des données :
- Préférences utilisateurs (couleurs personnalisées)
- Statistiques de jets de dés
- Préférences serveur (langue, préfixe, jet par défaut)
- Sauvegarde périodique toutes les 60 secondes

#### Parser d'expressions (DiceExpressionParser)

Analyse et évalue les expressions de dés :
- Support des notations standard : `2d6`, `1d20+5`, `3d8-2+1d4`
- Validation et parsing avec expressions régulières
- Gestion des modificateurs complexes

#### Gestionnaire de cache (CacheManager)

Classe utilitaire pour les manipulations thread-safe :
- Récupération et modification des couleurs utilisateur
- Incrémentation des statistiques
- Verrous pour éviter les race conditions

#### Système de traductions (TRANSLATIONS)

Dictionnaire multilingue pour l'internationalisation :
- Support de 4 langues (en, fr, de, es)
- Traductions des commandes help
- Messages d'embed personnalisés par langue

## Installation et démarrage

### Prérequis

- Python 3.8 ou supérieur
- Un bot Discord avec son token (créé sur le [Discord Developer Portal](https://discord.com/developers/applications))
- Intents activés : `messages`, `message_content`, `guilds`

### Installation

1. Cloner le repository
   ```bash
   git clone https://github.com/Phobetore/pi-Bot.git
   cd pi-Bot
   ```

2. Installer les dépendances
   ```bash
   pip install -r requirements.txt
   ```

3. Créer le fichier de configuration
   
   Créer un fichier `config.json` à la racine :
   ```json
   {
       "token": "VOTRE_TOKEN_DISCORD",
       "prefix": "!"
   }
   ```

4. Lancer le bot
   ```bash
   python main.py
   ```

Les fichiers JSON nécessaires seront créés automatiquement au premier démarrage.

## Guide d'utilisation

### Commandes pour les joueurs

#### Lancer des dés

```bash
# Syntaxe de base
!roll 2d6+3

# Avec un nom de cible
!roll 1d20+5 Goblin

# Raccourci
!r 2d8-2

# Utiliser le jet par défaut (si configuré)
!r
```

Expressions supportées :
- `XdY` : Lance X dés à Y faces
- `+N` / `-N` : Ajoute ou soustrait un modificateur
- Combinaisons : `2d6+1d4+3-1`

#### Personnaliser la couleur

```bash
# Définir sa couleur préférée
!setcolor bleu    # Options : bleu, rouge, vert, jaune

# Voir sa couleur actuelle
!getcolor
```

### Commandes pour les modérateurs

Permissions requises : `manage_guild` (Gérer le serveur)

#### Changer la langue

```bash
!setlang fr    # Options : en, fr, de, es
```

#### Définir un jet par défaut

```bash
!defaultRoll 1d20+5
```

Ce jet sera utilisé quand un joueur tape `!r` sans argument.

#### Changer le préfixe

```bash
!setprefix ?
```

### Commandes pour le propriétaire

#### Arrêter le bot

```bash
!stopbot
```

Sauvegarde le cache et arrête proprement le bot.

## Détails techniques pour contributeurs

### Système de gestion des erreurs

- **Cooldowns** : 1 commande roll toutes les 3 secondes par utilisateur
- **Max concurrency** : 1 exécution simultanée par utilisateur
- **Audit logging** : Jets supérieurs à 999 loggés automatiquement
- **Error handlers** : Gestion des erreurs de cooldown et permissions

### Performance et optimisation

Le cache en mémoire réduit drastiquement les I/O disque. Une task asyncio sauvegarde les données toutes les 60 secondes. Les locks asynchrones évitent les race conditions sur le cache. NumPy est utilisé pour les calculs sur les dés.

### Fichiers de données

Ces fichiers sont générés automatiquement et ignorés par git :

`user_preferences.json`
```json
{
  "colors": {
    "bleu": "0x3498db",
    "rouge": "0xe74c3c",
    "vert": "0x2ecc71",
    "jaune": "0xf1c40f"
  },
  "users": {
    "USER_ID": {
      "color": "bleu"
    }
  }
}
```

`user_stats.json`
```json
{
  "USER_ID": {
    "dice_rolls_count": 42
  }
}
```

`server_preferences.json`
```json
{
  "GUILD_ID": {
    "prefix": "!",
    "language": "fr",
    "default_roll": "1d20"
  }
}
```

### Logs d'audit

Le fichier `audit.log` enregistre :
- Jets de dés supérieurs à 999 (détection d'anomalies)
- Modifications des paramètres serveur
- Erreurs de chargement d'extensions
- Niveau : WARNING et supérieur

## Stack technique

- Python 3.8 ou supérieur
- [Py-Cord](https://docs.pycord.dev/) 2.6.1 - Framework Discord
- [NumPy](https://numpy.org/) 2.2.1 - Calculs numériques
- asyncio - Programmation asynchrone
- JSON - Persistance des données

## Contribution

Ce projet est avant tout personnel, mais les contributions sont bienvenues pour :
- Améliorer les performances
- Ajouter des fonctionnalités pertinentes
- Corriger des bugs
- Améliorer la documentation

Pour contribuer :
1. Fork le projet
2. Créez une branche (`git checkout -b feature/amelioration`)
3. Commitez vos changements (`git commit -m 'Ajout d'une fonctionnalité'`)
4. Push sur la branche (`git push origin feature/amelioration`)
5. Ouvrez une Pull Request

## Licence

Ce projet est fourni tel quel, sans garantie. Libre à vous de vous en inspirer ou de l'utiliser pour apprendre.

## Contact

Pour toute question ou suggestion : **core.layer**
