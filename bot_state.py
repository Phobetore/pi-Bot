"""Shared state and helpers for the Discord bot.

This module centralises global configuration, cache structures and helper
functions that need to be accessed from both the main bot entrypoint and the
cogs. Loading them from a dedicated module prevents accidental re-import of the
``main`` module, which can occur when the bot is executed as ``__main__`` (for
example under ``systemd``).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

__all__ = [
    "audit_logger",
    "CACHE",
    "config",
    "get_server_default_roll",
    "get_server_language",
    "is_server_allowed_for_cards",
    "set_server_default_roll",
    "set_server_language",
    "TRANSLATIONS",
]

CONFIG_PATH = Path(os.environ.get("PI_BOT_CONFIG", "config.json"))


def _load_config(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


config = _load_config(CONFIG_PATH)


# ─────────────────────────────────────────────
#          CONFIGURATION DES LOGS
# ─────────────────────────────────────────────
audit_logger = logging.getLogger("audit_logger")
audit_logger.setLevel(logging.WARNING)
if not any(isinstance(handler, logging.FileHandler) for handler in audit_logger.handlers):
    audit_handler = logging.FileHandler(filename="audit.log", encoding="utf-8", mode="a")
    audit_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    audit_logger.addHandler(audit_handler)


# ─────────────────────────────────────────────
#     CACHE EN MÉMOIRE (pour réduire I/O)
# ─────────────────────────────────────────────
CACHE = {
    "user_preferences": {},  # contenu de user_preferences.json (colors + users)
    "user_stats": {},        # contenu de user_stats.json
    "server_prefs": {},      # contenu de server_preferences.json
    "card_config": {},       # configuration des cartes
    "card_states": {}        # états des paquets par utilisateur
}


# ─────────────────────────────────────────────
#               Set des traductions
# ─────────────────────────────────────────────
TRANSLATIONS = {
    "en": {
        "help_title": "Bot Help",
        "help_description": "Below is a list of available commands:",
        "roll_title": "Roll Dice",
        "roll_desc": "Roll dice with an expression like 2d6+3. Optionally add a target name.",
        "setcolor_title": "Set Color",
        "setcolor_desc": "Define your preferred color for bot messages (options: bleu, rouge, vert, jaune).",
        "getcolor_title": "Get Color",
        "getcolor_desc": "Check your current preferred color.",
        "defaultroll_title": "Set Default Roll",
        "defaultroll_desc": "Set a default dice expression (requires `manage_guild`). If no argument is given to roll, the bot uses this default.",
        "setlang_title": "Change Bot Language",
        "setlang_desc": "Set the bot's default language for this server (requires `manage_guild`). Available: en, fr, de, es.",
        "setprefix_title": "Set Prefix",
        "setprefix_desc": "Define a custom prefix for this server (requires `manage_guild`).",
        "draw_title": "Draw Cards",
        "draw_desc": "Draw one or several cards from your personal deck. Specify a number to draw that many cards, or leave empty to fill your hand to 5 cards. Use --priv to receive the result via DM.",
        "draw_private_note": "*(Use `--priv` for a private draw.)*",
        "resetdeck_title": "Reset Deck",
        "resetdeck_desc": "Shuffle a fresh deck for yourself. Admins listed in the configuration can reset other users' decks by mentioning them.",
        "help_footer": "Contact core.layer for any feedback ❤️",
        "embed_result": "RESULT",
        "embed_for": "For",
        "embed_dice_details": "Dice Details:",
        "embed_calculation": "Calculation:",
        "embed_rolled_by": "Rolled by"
    },
    "fr": {
        "help_title": "Aide du Bot",
        "help_description": "Voici la liste des commandes disponibles :",
        "roll_title": "Lancer des Dés",
        "roll_desc": "Lancez des dés avec une expression comme 2d6+3. Vous pouvez ajouter un nom de cible.",
        "setcolor_title": "Définir la Couleur",
        "setcolor_desc": "Définissez votre couleur préférée (options : bleu, rouge, vert, jaune).",
        "getcolor_title": "Obtenir la Couleur",
        "getcolor_desc": "Obtenez votre couleur préférée actuelle.",
        "defaultroll_title": "Définir un Jet par Défaut",
        "defaultroll_desc": "Définissez un jet de dés par défaut (nécessite `manage_guild`). Si la commande roll est appelée sans argument, ce jet sera utilisé.",
        "setlang_title": "Changer la Langue",
        "setlang_desc": "Définit la langue par défaut du bot pour ce serveur (nécessite `manage_guild`). Langues : en, fr, de, es.",
        "setprefix_title": "Définir un Préfixe",
        "setprefix_desc": "Définit un préfixe personnalisé pour ce serveur (nécessite `manage_guild`).",
        "draw_title": "Piocher des Cartes",
        "draw_desc": "Pioche une ou plusieurs cartes de ton paquet personnel. Spécifie un nombre pour piocher exactement ce nombre de cartes, ou laisse vide pour remplir ta main à 5 cartes. Utilise --priv pour recevoir le résultat en MP.",
        "draw_private_note": "*(Option `--priv` pour un tirage privé.)*",
        "resetdeck_title": "Réinitialiser le Paquet",
        "resetdeck_desc": "Reconstitue un nouveau paquet pour toi. Les administrateurs configurés peuvent réinitialiser le paquet d'un autre membre en le mentionnant.",
        "help_footer": "Contactez core.layer pour tout retour ❤️",
        "embed_result": "RÉSULTAT",
        "embed_for": "Pour",
        "embed_dice_details": "Détails des dés :",
        "embed_calculation": "Calcul :",
        "embed_rolled_by": "Lancé par"
    },
    "de": {
        "help_title": "Bot-Hilfe",
        "help_description": "Hier ist eine Liste der verfügbaren Befehle:",
        "roll_title": "Würfeln",
        "roll_desc": "Würfle mit einem Ausdruck wie 2d6+3. Optional kann ein Zielname hinzugefügt werden.",
        "setcolor_title": "Farbe Einstellen",
        "setcolor_desc": "Lege deine bevorzugte Farbe für Bot-Nachrichten fest (bleu, rouge, vert, jaune).",
        "getcolor_title": "Farbe Abfragen",
        "getcolor_desc": "Zeigt deine aktuelle bevorzugte Farbe an.",
        "defaultroll_title": "Standardwurf Setzen",
        "defaultroll_desc": "Setzt einen Standardwurf (benötigt `manage_guild`). Wenn du roll ohne Argument nutzt, wird dieser Standardwurf verwendet.",
        "setlang_title": "Sprache Ändern",
        "setlang_desc": "Setzt die Standardsprache für diesen Server (benötigt `manage_guild`). Verfügbar: en, fr, de, es.",
        "setprefix_title": "Präfix Einstellen",
        "setprefix_desc": "Lege ein benutzerdefiniertes Präfix für diesen Server fest (benötigt `manage_guild`).",
        "draw_title": "Karten Ziehen",
        "draw_desc": "Ziehe eine oder mehrere Karten aus deinem persönlichen Deck. Gib eine Zahl an, um genau diese Anzahl an Karten zu ziehen, oder lasse es leer, um deine Hand auf 5 Karten aufzufüllen. Verwende --priv für eine private Nachricht.",
        "draw_private_note": "*(Verwende `--priv` für eine private Ziehung.)*",
        "resetdeck_title": "Deck Zurücksetzen",
        "resetdeck_desc": "Mische ein frisches Deck für dich. In der Konfiguration eingetragene Administratoren können auch Decks anderer Nutzer zurücksetzen.",
        "help_footer": "Kontaktieren Sie core.layer für Feedback ❤️",
        "embed_result": "ERGEBNIS",
        "embed_for": "Für",
        "embed_dice_details": "Würfel Details:",
        "embed_calculation": "Berechnung:",
        "embed_rolled_by": "Gewürfelt von"
    },
    "es": {
        "help_title": "Ayuda del Bot",
        "help_description": "Esta es la lista de los comandos disponibles:",
        "roll_title": "Lanzar Dados",
        "roll_desc": "Lanza dados con una expresión como 2d6+3. Agrega un nombre de objetivo opcional.",
        "setcolor_title": "Configurar Color",
        "setcolor_desc": "Define tu color preferido para los mensajes del bot (bleu, rouge, vert, jaune).",
        "getcolor_title": "Obtener Color",
        "getcolor_desc": "Consulta tu color preferido actual.",
        "defaultroll_title": "Establecer Tirada por Defecto",
        "defaultroll_desc": "Establece una tirada de dados por defecto (requiere `manage_guild`). Si no hay argumento en roll, se usará esta tirada.",
        "setlang_title": "Cambiar Idioma",
        "setlang_desc": "Configura el idioma predeterminado del bot en este servidor (requiere `manage_guild`). Disponible: en, fr, de, es.",
        "setprefix_title": "Establecer Prefijo",
        "setprefix_desc": "Define un prefijo personalizado para este servidor (requiere `manage_guild`).",
        "draw_title": "Robar Cartas",
        "draw_desc": "Roba una o varias cartas de tu mazo personal. Especifica un número para robar exactamente esa cantidad de cartas, o déjalo vacío para llenar tu mano a 5 cartas. Usa --priv para recibir el resultado por mensaje privado.",
        "draw_private_note": "*(Utiliza `--priv` para un robo privado.)*",
        "resetdeck_title": "Restablecer Mazo",
        "resetdeck_desc": "Baraja un nuevo mazo para ti. Los administradores configurados pueden restablecer el mazo de otro usuario mencionándolo.",
        "help_footer": "Contacta a core.layer para cualquier comentario ❤️",
        "embed_result": "RESULTADO",
        "embed_for": "Para",
        "embed_dice_details": "Detalles de los dados:",
        "embed_calculation": "Cálculo:",
        "embed_rolled_by": "Lanzado por"
    }
}


# ─────────────────────────────────────────────
#               Helper functions
# ─────────────────────────────────────────────
def get_server_language(guild_id: int) -> str:
    """Récupère la langue du serveur dans le cache (par défaut 'en')."""
    return CACHE["server_prefs"].get(str(guild_id), {}).get("language", "en")


def set_server_language(guild_id: int, lang: str) -> None:
    """Modifie la langue du serveur dans le cache."""
    if str(guild_id) not in CACHE["server_prefs"]:
        CACHE["server_prefs"][str(guild_id)] = {}
    CACHE["server_prefs"][str(guild_id)]["language"] = lang
    audit_logger.warning(f"Language changed to {lang} for guild {guild_id}")


def get_server_default_roll(guild_id: int) -> Optional[str]:
    """Récupère le jet par défaut pour le serveur. Retourne None s'il n'est pas défini."""
    server_data = CACHE["server_prefs"].get(str(guild_id), {})
    return server_data.get("default_roll", None)


def set_server_default_roll(guild_id: int, expression: str) -> None:
    """Définit (ou met à jour) le jet par défaut pour le serveur."""
    if str(guild_id) not in CACHE["server_prefs"]:
        CACHE["server_prefs"][str(guild_id)] = {}
    CACHE["server_prefs"][str(guild_id)]["default_roll"] = expression
    audit_logger.warning(f"Default dice roll '{expression}' set for guild {guild_id}")


def is_server_allowed_for_cards(guild_id: Optional[int]) -> bool:
    """Vérifie si le serveur peut utiliser les commandes de cartes."""
    if guild_id is None:
        return False
    card_config = CACHE.get("card_config", {}) or {}
    allowed_server_id = card_config.get("allowed_server_id")
    if allowed_server_id in (None, "0", ""):
        return True
    return str(guild_id) == str(allowed_server_id)
