import discord
from discord.ext import commands, tasks
import json
import logging
import os
import asyncio
import inspect
import time

# ─────────────────────────────────────────────
#          CONFIGURATION DES LOGS
# ─────────────────────────────────────────────

# Logger pour l'audit (audit.log) - on y met WARNING/ERROR
audit_logger = logging.getLogger("audit_logger")
audit_logger.setLevel(logging.WARNING)
audit_handler = logging.FileHandler(filename="audit.log", encoding="utf-8", mode="a")
audit_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
audit_logger.addHandler(audit_handler)


# ─────────────────────────────────────────────
#        CHARGEMENT DE LA CONFIG
# ─────────────────────────────────────────────
with open("config.json", "r") as f:
    config = json.load(f)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True

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

LAST_SAVE_TIME = time.time()
SAVE_INTERVAL = 60  # Sauvegarde toutes les 60 secondes (ajustable)

# ─────────────────────────────────────────────
#       INITIALISATION DES FICHIERS JSON
# ─────────────────────────────────────────────
def init_json_files():
    # user_preferences.json
    if not os.path.exists("user_preferences.json"):
        with open("user_preferences.json", "w", encoding="utf-8") as f:
            json.dump({
                "colors": {
                    "bleu": "0x3498db",
                    "rouge": "0xe74c3c",
                    "vert": "0x2ecc71",
                    "jaune": "0xf1c40f"
                },
                "users": {}
            }, f, indent=4)

    # user_stats.json
    if not os.path.exists("user_stats.json"):
        with open("user_stats.json", "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)

    # server_preferences.json
    if not os.path.exists("server_preferences.json"):
        with open("server_preferences.json", "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)

    # card_config.json (configuration générale des cartes)
    if not os.path.exists("card_config.json"):
        with open("card_config.json", "w", encoding="utf-8") as f:
            json.dump({
                "allowed_server_id": "0",
                "admin_users": [],
                "cards": [
                    {
                        "id": "fireball",
                        "name": "Boule de Feu",
                        "image": None,
                        "description": "Retire deux tuiles du deck adverse. Inflige Volonté × 0,5 en dégâts et applique Traitement × 0,5 en vitesse. Largeur 2,5 m, malus d'évitement de 5 %.",
                        "category": "Attaque",
                        "values": {
                            "degats": "Volonté × 0,5",
                            "vitesse": "Traitement × 0,5",
                            "largeur": "2,5 m",
                            "malus_evitement": "5 %"
                        },
                        "effects": [
                            "Retire deux tuiles du deck adverse.",
                            "Les effets se matérialisent dans la réalité; l'utilisateur subit ses propres dégâts si l'adversaire est encore debout lorsque le deck est vide."
                        ],
                        "price": {"standard": 30, "deluxe": 150}
                    },
                    {
                        "id": "wind_gust",
                        "name": "Bourrasque",
                        "image": None,
                        "description": "Renvoie un projectile à la moitié de sa puissance (fonctionne sur les attaques ≤ Volonté × 0,5). Contre automatiquement les Boules de Feu et retire une tuile du deck adverse.",
                        "category": "Défense",
                        "values": {
                            "renvoi": "½ de la puissance subie",
                            "seuil": "Attaques ≤ Volonté × 0,5"
                        },
                        "effects": [
                            "Protège contre Boule de Feu et retire une tuile du deck adverse.",
                            "Ne fonctionne que si la puissance adverse est inférieure ou égale au seuil indiqué."
                        ],
                        "price": {"standard": 30, "deluxe": 150}
                    },
                    {
                        "id": "ice_spike",
                        "name": "Pique de Givre",
                        "image": None,
                        "description": "Ignore les défenses et inflige Volonté × 0,25 en dégâts avec une vitesse Traitement × 0,5. Retire une tuile du deck adverse.",
                        "category": "Attaque",
                        "values": {
                            "degats": "Volonté × 0,25",
                            "vitesse": "Traitement × 0,5"
                        },
                        "effects": [
                            "Ignore les défenses.",
                            "Retire une tuile du deck adverse."
                        ],
                        "price": {"standard": 30, "deluxe": 150}
                    },
                    {
                        "id": "earth_wall",
                        "name": "Mur de Terre",
                        "image": None,
                        "description": "Mur défensif qui bloque tous les types d'attaque avec une force égale à Volonté × 0,5.",
                        "category": "Défense",
                        "values": {
                            "blocage": "Volonté × 0,5"
                        },
                        "effects": [
                            "Peut bloquer tout type d'attaque.",
                            "Annule les dégâts reçus tant que la force du mur n'est pas dépassée."
                        ],
                        "price": {"standard": 30, "deluxe": 150}
                    }
                ],
                "default_deck": [
                    {"card_id": "fireball", "count": 5},
                    {"card_id": "wind_gust", "count": 5},
                    {"card_id": "ice_spike", "count": 5},
                    {"card_id": "earth_wall", "count": 5}
                ],
                "user_decks": {}
            }, f, indent=4)

    # card_states.json (état actuel des paquets)
    if not os.path.exists("card_states.json"):
        with open("card_states.json", "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)


def load_json_files_into_cache():
    """Charge les données des JSON dans le cache en mémoire."""
    try:
        with open("user_preferences.json", "r", encoding="utf-8") as f:
            CACHE["user_preferences"] = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        CACHE["user_preferences"] = {}

    try:
        with open("user_stats.json", "r", encoding="utf-8") as f:
            CACHE["user_stats"] = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        CACHE["user_stats"] = {}

    try:
        with open("server_preferences.json", "r", encoding="utf-8") as f:
            CACHE["server_prefs"] = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        CACHE["server_prefs"] = {}

    try:
        with open("card_config.json", "r", encoding="utf-8") as f:
            CACHE["card_config"] = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        CACHE["card_config"] = {}

    try:
        with open("card_states.json", "r", encoding="utf-8") as f:
            CACHE["card_states"] = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        CACHE["card_states"] = {}


async def save_cache_to_json_files():
    """Persist the in-memory cache to JSON files using a single lock."""
    from cogs.dice_rolls import CacheManager
    try:
        from cogs.card_draws import DeckManager
    except ImportError:
        DeckManager = None

    async with CacheManager._lock:
        # user_preferences
        with open("user_preferences.json", "w", encoding="utf-8") as f:
            json.dump(CACHE["user_preferences"], f, indent=4)

        # user_stats
        with open("user_stats.json", "w", encoding="utf-8") as f:
            json.dump(CACHE["user_stats"], f, indent=4)

        # server_preferences
        with open("server_preferences.json", "w", encoding="utf-8") as f:
            json.dump(CACHE["server_prefs"], f, indent=4)

    if DeckManager is not None:
        async with DeckManager._lock:
            with open("card_states.json", "w", encoding="utf-8") as f:
                json.dump(CACHE["card_states"], f, indent=4)
    else:
        with open("card_states.json", "w", encoding="utf-8") as f:
            json.dump(CACHE["card_states"], f, indent=4)

init_json_files()
load_json_files_into_cache()

# ─────────────────────────────────────────────
#     FONCTION DYNAMIQUE DE PRÉFIXE
# ─────────────────────────────────────────────
def get_server_prefix(bot, message):
    """
    Récupère le préfixe personnalisé d'un serveur si défini,
    sinon retourne le préfixe de config.json.
    """
    if message.guild is None:
        # Si message privé ou pas de guilde
        return config["prefix"]

    guild_id = str(message.guild.id)
    return CACHE["server_prefs"].get(guild_id, {}).get("prefix", config["prefix"])


# ─────────────────────────────────────────────
#   CRÉATION DU BOT AVEC PRÉFIXE DYNAMIQUE
# ─────────────────────────────────────────────
bot = commands.Bot(command_prefix=get_server_prefix, intents=intents, help_command=None)

# ─────────────────────────────────────────────
#       TÂCHE ASYNCHRONE DE SAUVEGARDE
# ─────────────────────────────────────────────
@tasks.loop(seconds=SAVE_INTERVAL)
async def periodic_saver():
    """Tâche asynchrone qui sauvegarde le cache dans les fichiers JSON."""
    await save_cache_to_json_files()

@bot.event
async def on_ready():
    print(f"Bot connecté : {bot.user.name}")
    if not periodic_saver.is_running():
        periodic_saver.start()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ Command not found. Use `{ctx.prefix}help` to see the available commands.")
    else:
        audit_logger.error(f"Unexpected error: {error}")

# ─────────────────────────────────────────────
#     MULTILINGUE : GET/SET LANGUE
# ─────────────────────────────────────────────
def get_server_language(guild_id: int) -> str:
    """Récupère la langue du serveur dans le cache (par défaut 'en')."""
    return CACHE["server_prefs"].get(str(guild_id), {}).get("language", "en")

def set_server_language(guild_id: int, lang: str):
    """Modifie la langue du serveur dans le cache."""
    if str(guild_id) not in CACHE["server_prefs"]:
        CACHE["server_prefs"][str(guild_id)] = {}
    CACHE["server_prefs"][str(guild_id)]["language"] = lang
    audit_logger.warning(f"Language changed to {lang} for guild {guild_id}")

@bot.command(name="setlang")
@commands.has_permissions(manage_guild=True)
async def set_language_command(ctx, lang: str):
    """
    Définit la langue par défaut du bot pour ce serveur.
    Langues disponibles: en, fr, de, es.
    """
    lang = lang.lower()
    if lang not in ["en", "fr", "de", "es"]:
        await ctx.send("❌ Invalid language code. Please choose among: en, fr, de, es.")
        return

    set_server_language(ctx.guild.id, lang)
    await ctx.send(f"✅ Language is now set to: **{lang}** (server-wide).")

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
        "draw_desc": "Draw one or several cards from your personal deck. Use --priv to receive the result via DM.",
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
        "draw_desc": "Pioche une ou plusieurs cartes de ton paquet personnel. Utilise --priv pour recevoir le résultat en MP.",
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
        "draw_desc": "Ziehe eine oder mehrere Karten aus deinem persönlichen Deck. Verwende --priv für eine private Nachricht.",
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
        "draw_desc": "Roba una o varias cartas de tu mazo personal. Usa --priv para recibir el resultado por mensaje privado.",
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
#               Dés par defauts
# ─────────────────────────────────────────────
def get_server_default_roll(guild_id: int) -> str:
    """
    Récupère le jet par défaut pour le serveur.
    Retourne None s'il n'est pas défini.
    """
    server_data = CACHE["server_prefs"].get(str(guild_id), {})
    return server_data.get("default_roll", None)

def set_server_default_roll(guild_id: int, expression: str):
    """
    Définit (ou met à jour) le jet par défaut pour le serveur.
    """
    if str(guild_id) not in CACHE["server_prefs"]:
        CACHE["server_prefs"][str(guild_id)] = {}
    CACHE["server_prefs"][str(guild_id)]["default_roll"] = expression
    
    # Petit log d'audit
    audit_logger.warning(f"Default dice roll '{expression}' set for guild {guild_id}")

@bot.command(name="defaultRoll")
@commands.has_permissions(manage_guild=True)
async def default_roll_command(ctx, *, expression: str):
    """
    Définir le jet de dés par défaut pour ce serveur.
    Exemple: !defaultroll 1d20+3
    """
    if len(expression) > 50:
        await ctx.send("❌ Expression trop longue. Maximum 50 caractères.")
        return

    if 'd' not in expression:
        await ctx.send("❌ Format invalide. Vous devez inclure au moins 'd', ex: 1d20.")
        return

    set_server_default_roll(ctx.guild.id, expression)
    await ctx.send(f"✅ Le jet de dés par défaut est maintenant : `{expression}`")


# ─────────────────────────────────────────────
#         COMMANDE POUR CHANGER DE PRÉFIXE
# ─────────────────────────────────────────────
@bot.command(name="setprefix")
@commands.has_permissions(manage_guild=True)
async def set_prefix_command(ctx, *, prefix: str):
    """
    Permet de définir un préfixe personnalisé pour le serveur.
    Exemple : !setprefix ?
    """
    if len(prefix) > 5:
        await ctx.send("❌ Le préfixe est trop long. Maximum : 5 caractères.")
        return

    guild_id = str(ctx.guild.id)
    if guild_id not in CACHE["server_prefs"]:
        CACHE["server_prefs"][guild_id] = {}

    CACHE["server_prefs"][guild_id]["prefix"] = prefix
    await ctx.send(f"✅ Le préfixe pour ce serveur est maintenant : `{prefix}`")

    audit_logger.warning(f"Prefix changed to '{prefix}' for guild {ctx.guild.name} ({guild_id})")


# ─────────────────────────────────────────────
#               COMMANDE D'AIDE
# ─────────────────────────────────────────────
@bot.command(name="help", aliases=["h"])
async def help_command(ctx):
    """
    Affiche une documentation plus lisible sur les commandes disponibles.
    """
    # Détermination de la langue
    guild_lang = get_server_language(ctx.guild.id) if ctx.guild else "en"
    tr = TRANSLATIONS.get(guild_lang, TRANSLATIONS["en"])

    # Récupère le préfixe du serveur
    server_prefix = (ctx.clean_prefix or config["prefix"]).strip()

    # Couleur et création de l'embed
    embed_color = discord.Color.purple()
    embed = discord.Embed(
        title=f"**{tr['help_title']}**",
        description=(
            f"{tr['help_description']}\n"
            f"_({server_prefix}help pour réafficher cette aide)_\n"
        ),
        color=embed_color
    )

    # Thumbnail en haut à droite (facultatif)
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/718585329459789845/1332420668783984762/image2_bg.png")

    # ─────────────────────────────────────────────
    #  1) ROLL / R
    # ─────────────────────────────────────────────
    embed.add_field(
        name=f"🎲 **{server_prefix}roll / {server_prefix}r** — {tr['roll_title']}",
        value=(
            f"{tr['roll_desc']}\n\n"
            f"**Exemple :**\n"
            f"```yaml\n{server_prefix}roll 2d6+3 Goblin\n```\n"
        ),
        inline=False
    )

    # ─────────────────────────────────────────────
    #  2) SETCOLOR
    # ─────────────────────────────────────────────
    embed.add_field(
        name=f"🎨 **{server_prefix}setcolor** — {tr['setcolor_title']}",
        value=(
            f"{tr['setcolor_desc']}\n\n"
            f"**Exemple :**\n"
            f"```yaml\n{server_prefix}setcolor rouge\n```\n"
            f"*(Options : bleu, rouge, vert, jaune)*"
        ),
        inline=False
    )

    # ─────────────────────────────────────────────
    #  3) GETCOLOR
    # ─────────────────────────────────────────────
    embed.add_field(
        name=f"✏️ **{server_prefix}getcolor** — {tr['getcolor_title']}",
        value=(
            f"{tr['getcolor_desc']}\n\n"
            f"**Exemple :**\n"
            f"```yaml\n{server_prefix}getcolor\n```"
        ),
        inline=False
    )

    # ─────────────────────────────────────────────
    #  4) DEFAULTROLL
    # ─────────────────────────────────────────────
    embed.add_field(
        name=f"🔁 **{server_prefix}defaultRoll** — {tr['defaultroll_title']}",
        value=(
            f"{tr['defaultroll_desc']}\n\n"
            f"**Exemple :**\n"
            f"```yaml\n{server_prefix}defaultRoll 1d20\n```\n"
            f"**Note :** Seuls les membres disposant de la permission "
            f"`manage_guild` peuvent définir le jet par défaut."
        ),
        inline=False
    )

    # ─────────────────────────────────────────────
    #  5) SETLANG
    # ─────────────────────────────────────────────
    embed.add_field(
        name=f"🌐 **{server_prefix}setlang** — {tr['setlang_title']}",
        value=(
            f"{tr['setlang_desc']}\n\n"
            f"**Exemple :**\n"
            f"```yaml\n{server_prefix}setlang fr\n```\n"
            f"**Note :** Permission `manage_guild` requise."
        ),
        inline=False
    )

    # ─────────────────────────────────────────────
    #  6) SETPREFIX
    # ─────────────────────────────────────────────
    embed.add_field(
        name=f"🔧 **{server_prefix}setprefix** — {tr['setprefix_title']}",
        value=(
            f"{tr['setprefix_desc']}\n\n"
            f"**Exemple :**\n"
            f"```yaml\n{server_prefix}setprefix ?\n```\n"
            f"**Note :** Permission `manage_guild` requise."
        ),
        inline=False
    )

    # ─────────────────────────────────────────────
    #  7) PIOCHE / P
    # ─────────────────────────────────────────────
    embed.add_field(
        name=f"🃏 **{server_prefix}pioche / {server_prefix}p** — {tr['draw_title']}",
        value=(
            f"{tr['draw_desc']}\n\n"
            f"**Exemples :**\n"
            f"```yaml\n{server_prefix}pioche\n{server_prefix}pioche 3 --priv\n```\n"
            f"{tr['draw_private_note']}"
        ),
        inline=False
    )

    # ─────────────────────────────────────────────
    #  8) RESETDECK / RD
    # ─────────────────────────────────────────────
    embed.add_field(
        name=f"🆕 **{server_prefix}resetDeck / {server_prefix}rd** — {tr['resetdeck_title']}",
        value=(
            f"{tr['resetdeck_desc']}\n\n"
            f"**Exemple :**\n"
            f"```yaml\n{server_prefix}resetDeck\n```"
        ),
        inline=False
    )

    # Footer
    embed.set_footer(text=tr["help_footer"])
    await ctx.send(embed=embed)


# ─────────────────────────────────────────────
#          CHARGEMENT DU COG
# ─────────────────────────────────────────────
startup_extensions = ["cogs.dice_rolls", "cogs.card_draws"]


async def load_startup_extensions():
    for extension in startup_extensions:
        try:
            maybe_coro = bot.load_extension(extension)
            if inspect.isawaitable(maybe_coro):
                await maybe_coro
        except Exception as e:
            audit_logger.error(f"Error loading extension {extension}: {e}")

# ─────────────────────────────────────────────
#          ARRÊT PROPRE DU BOT
# ─────────────────────────────────────────────
@bot.command(name="stopbot", hidden=True)
@commands.is_owner()
async def stop_bot(ctx):
    """Arrête le bot proprement (sauvegarde cache, arrête la loop)."""
    await ctx.send("Bot is shutting down...")
    if periodic_saver.is_running():
        periodic_saver.cancel()
    await save_cache_to_json_files()
    await bot.close()

# ─────────────────────────────────────────────
#          LANCEMENT DU BOT
# ─────────────────────────────────────────────
async def run_bot():
    try:
        await load_startup_extensions()
        await bot.start(config["token"])
    finally:
        if periodic_saver.is_running():
            periodic_saver.cancel()
        await save_cache_to_json_files()


if __name__ == "__main__":
    asyncio.run(run_bot())
