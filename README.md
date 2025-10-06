# 🎲 pi-Bot

Bot Discord spécialisé dans la gestion de jets de dés pour jeux de rôle, conçu avec [Py-Cord](https://docs.pycord.dev/). Ce projet démontre une architecture propre, modulaire et performante pour un bot Discord en Python.

> **Note :** Ce projet n'est pas destiné à être massivement réutilisé, mais plutôt à servir de vitrine de compétences techniques et à permettre à des contributeurs motivés de participer à son évolution.

---

## 📋 Vue d'ensemble

pi-Bot est un bot Discord qui gère les jets de dés avec de nombreuses options de personnalisation. Il offre une expérience utilisateur fluide pour les joueurs et maîtres de jeu, avec support multilingue et personnalisation avancée.

### ✨ Fonctionnalités principales

- **🎲 Jets de dés flexibles** : Expressions complexes type `2d6+3`, `1d20+5-2`, avec support de multiples dés et modificateurs
- **🎨 Personnalisation des couleurs** : Chaque utilisateur choisit la couleur de ses messages
- **🌐 Support multilingue** : Français, anglais, allemand et espagnol
- **🔧 Préfixe configurable** : Personnalisation par serveur
- **🔁 Jet par défaut** : Définition d'un jet de dés par défaut par serveur
- **💾 Cache en mémoire** : Système de cache optimisé pour réduire les I/O disque
- **📊 Statistiques** : Suivi des jets de dés par utilisateur
- **🔒 Audit logging** : Logs des actions importantes

---

## 🏗️ Architecture technique

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

#### 1. **Système de cache** (`CACHE`)
Cache en mémoire avec verrous asynchrones (`asyncio.Lock`) pour garantir la cohérence des données :
- Préférences utilisateurs (couleurs)
- Statistiques de jets de dés
- Préférences serveur (langue, préfixe, jet par défaut)
- Sauvegarde périodique toutes les 60 secondes

#### 2. **Parser d'expressions** (`DiceExpressionParser`)
Analyse et évalue les expressions de dés :
- Support des notations standard : `2d6`, `1d20+5`, `3d8-2+1d4`
- Validation et parsing avec regex
- Gestion des modificateurs complexes

#### 3. **Gestionnaire de cache** (`CacheManager`)
Classe utilitaire pour manipulations thread-safe :
- Récupération/modification des couleurs utilisateur
- Incrémentation des statistiques
- Utilisation de verrous pour éviter les race conditions

#### 4. **Système de traductions** (`TRANSLATIONS`)
Dictionnaire multilingue pour l'internationalisation (i18n) :
- Support de 4 langues (en, fr, de, es)
- Traductions des commandes help
- Messages d'embed personnalisés par langue

---

## 🚀 Installation et démarrage

### Prérequis

- Python 3.8+
- Un bot Discord avec son token (créé sur [Discord Developer Portal](https://discord.com/developers/applications))
- Intents activés : `messages`, `message_content`, `guilds`

### Installation

1. **Cloner le repository**
   ```bash
   git clone https://github.com/Phobetore/pi-Bot.git
   cd pi-Bot
   ```

2. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

3. **Créer le fichier de configuration**
   
   Créer un fichier `config.json` à la racine :
   ```json
   {
       "token": "VOTRE_TOKEN_DISCORD",
       "prefix": "!"
   }
   ```

4. **Lancer le bot**
   ```bash
   python main.py
   ```

Le bot créera automatiquement les fichiers JSON nécessaires au premier démarrage.

---

## 📖 Guide d'utilisation

### Commandes pour les joueurs

#### 🎲 Lancer des dés
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

**Expressions supportées :**
- `XdY` : Lance X dés à Y faces
- `+N` / `-N` : Ajoute/soustrait un modificateur
- Combinaisons : `2d6+1d4+3-1`

#### 🎨 Personnaliser la couleur
```bash
# Définir sa couleur préférée
!setcolor bleu    # Options : bleu, rouge, vert, jaune

# Voir sa couleur actuelle
!getcolor
```

### Commandes pour les modérateurs

> **Permissions requises :** `manage_guild` (Gérer le serveur)

#### 🌐 Changer la langue
```bash
!setlang fr    # Options : en, fr, de, es
```

#### 🔁 Définir un jet par défaut
```bash
!defaultRoll 1d20+5
```
Ce jet sera utilisé quand un joueur tape `!r` sans argument.

#### 🔧 Changer le préfixe
```bash
!setprefix ?
```

### Commandes pour le propriétaire

#### 🛑 Arrêter le bot
```bash
!stopbot
```
Sauvegarde le cache et arrête proprement le bot.

---

## 🧪 Détails techniques pour contributeurs

### Système de gestion des erreurs

- **Cooldowns** : 1 commande roll toutes les 3 secondes par utilisateur
- **Max concurrency** : 1 exécution simultanée par utilisateur
- **Audit logging** : Jets > 999 loggés automatiquement
- **Error handlers** : Gestion des erreurs de cooldown et permissions

### Performance et optimisation

1. **Cache en mémoire** : Réduction drastique des I/O disque
2. **Sauvegarde périodique** : Task asyncio toutes les 60s
3. **Locks asynchrones** : Évite les race conditions sur le cache
4. **Numpy pour les calculs** : Utilisation de numpy pour les opérations sur les dés

### Fichiers de données

Tous ces fichiers sont auto-générés et ignorés par git :

**`user_preferences.json`**
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

**`user_stats.json`**
```json
{
  "USER_ID": {
    "dice_rolls_count": 42
  }
}
```

**`server_preferences.json`**
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
- Jets de dés > 999 (détection d'anomalies)
- Modifications des paramètres serveur
- Erreurs de chargement d'extensions
- Niveau : WARNING et supérieur

---

## 🛠️ Stack technique

- **Python 3.8+**
- **[Py-Cord](https://docs.pycord.dev/) 2.6.1** : Framework Discord
- **[NumPy](https://numpy.org/) 2.2.1** : Calculs numériques
- **asyncio** : Programmation asynchrone
- **JSON** : Persistance des données

---

## 🤝 Contribution

Ce projet est principalement personnel, mais les contributions sont les bienvenues si vous souhaitez :
- Améliorer les performances
- Ajouter des fonctionnalités pertinentes
- Corriger des bugs
- Améliorer la documentation

**Pour contribuer :**
1. Fork le projet
2. Créez une branche (`git checkout -b feature/amelioration`)
3. Commitez vos changements (`git commit -m 'Ajout d'une fonctionnalité'`)
4. Push sur la branche (`git push origin feature/amelioration`)
5. Ouvrez une Pull Request

---

## 📝 Licence

Ce projet est fourni tel quel, sans garantie. Utilisez-le librement pour apprendre ou vous en inspirer.

---

## 📧 Contact

Pour toute question ou suggestion : **core.layer**

---

**Développé avec ❤️ pour la communauté Discord et les amateurs de JDR**
