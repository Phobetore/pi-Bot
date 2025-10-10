import asyncio
import random
from typing import Dict, List, Optional, Set, Tuple

import discord
from discord.ext import commands

from bot_state import CACHE, audit_logger, config, get_server_language


CARD_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "not_available": "❌ This command is not available on this server.",
        "draw_invalid_count": "❌ The number of cards must be greater than 0.",
        "draw_multiple_counts": "❌ You can only specify one number of cards to draw.",
        "draw_unexpected_argument": "❌ Unknown argument. Use `{prefix}pioche [number] [--priv]` (e.g. `{prefix}pioche 3 --priv`).",
        "deck_empty_config": "❌ The configured deck is empty. Check the tile configuration.",
        "draw_embed_title": "🪄 Tile Draw",
        "auto_reset_footer": "A new deck has been built and shuffled.",
        "field_tiles": "Tiles",
        "default_card_name": "Tile",
        "draw_deck_empty": "The deck is empty, no cards left to draw.",
        "draw_none": "No card could be drawn.",
        "draw_hand_full": "Your hand is already full (5 tiles).",
        "draw_deck_not_enough": "The deck does not contain enough tiles to fill your hand.",
        "field_hand": "Current hand",
        "hand_empty": "(no tiles in hand)",
        "field_remaining": "Remaining tiles",
        "field_discard": "Discarded tiles",
        "field_turn_action": "Turn action",
        "turn_action_value": "Use `{prefix}joue <indexes>` to align up to three tiles (e.g. `{prefix}joue 1 3`).",
        "draw_deck_empty_footer": "The deck is empty. If the encounter continues, use `{prefix}resetDeck` to start again.",
        "dm_failed": "⚠️ Unable to send a private message. Please allow DMs from the server.",
        "dm_sent": "📬 Result sent via private message.",
        "play_missing_indices": "❌ Provide the positions of the tiles to use (e.g. `{prefix}joue 1 2`).",
        "play_invalid_index": "❌ Positions must be valid numbers.",
        "play_too_many": "❌ You can only align three tiles per turn.",
        "play_invalid_parameters": "❌ Invalid parameters for the `{prefix}joue` command.",
        "play_no_indices": "❌ Provide at least one tile to use.",
        "play_empty_hand": "❌ Your hand is empty. Use `{prefix}pioche` to draw tiles.",
        "play_out_of_range": "❌ One of the requested positions does not exist in your current hand.",
        "play_duplicate_index": "❌ Each position can be used only once per command.",
        "play_generic_error": "❌ Unable to use these tiles at the moment.",
        "play_embed_title": "⚔️ Tiles aligned",
        "field_resolution": "Resolution",
        "field_remaining_hand": "Remaining hand",
        "footer_draw_prompt": "Use `{prefix}pioche` to refill your hand up to five tiles.",
        "play_deck_empty_footer": "The deck is now empty. Consider `{prefix}resetDeck` if a new round begins.",
        "reset_not_allowed": "⛔ This action is reserved for authorised administrators.",
        "reset_self": "🆕 Your deck has been rebuilt and shuffled. Use `{prefix}pioche` to draw a five-tile hand.",
        "reset_other": "🆕 {mention}'s deck has been rebuilt and shuffled. Invite them to use `{prefix}pioche` to rebuild their hand.",
        "reset_dm": "🃏 Your tile deck was reset by {actor}.",
    },
    "fr": {
        "not_available": "❌ Cette commande n'est pas disponible sur ce serveur.",
        "draw_invalid_count": "❌ Le nombre de cartes doit être supérieur à 0.",
        "draw_multiple_counts": "❌ Vous ne pouvez spécifier qu'un seul nombre de cartes à piocher.",
        "draw_unexpected_argument": "❌ Argument inconnu. Utilisez `{prefix}pioche [nombre] [--priv]` (ex. `{prefix}pioche 3 --priv`).",
        "deck_empty_config": "❌ Le paquet configuré est vide. Vérifiez la configuration des tuiles.",
        "draw_embed_title": "🪄 Pioche des Tuiles",
        "auto_reset_footer": "Un nouveau paquet a été constitué et mélangé.",
        "field_tiles": "Tuiles",
        "default_card_name": "Tuile",
        "draw_deck_empty": "Le paquet est vide, aucune carte à piocher.",
        "draw_none": "Aucune carte n'a pu être piochée.",
        "draw_hand_full": "Votre main est déjà complète (5 tuiles).",
        "draw_deck_not_enough": "Le paquet ne contient plus assez de tuiles pour compléter votre main.",
        "field_hand": "Main actuelle",
        "hand_empty": "(aucune tuile en main)",
        "field_remaining": "Tuiles restantes",
        "field_discard": "Tuiles défaussées",
        "field_turn_action": "Action du tour",
        "turn_action_value": "Utilisez `{prefix}joue <indices>` pour aligner jusqu'à trois tuiles (ex. `{prefix}joue 1 3`).",
        "draw_deck_empty_footer": "Le paquet est vide. Si l'affrontement continue, utilisez `{prefix}resetDeck` pour recommencer.",
        "dm_failed": "⚠️ Impossible d'envoyer un message privé. Merci d'autoriser les DM du serveur.",
        "dm_sent": "📬 Résultat envoyé en message privé.",
        "play_missing_indices": "❌ Indiquez les positions des tuiles à utiliser (ex. `{prefix}joue 1 2`).",
        "play_invalid_index": "❌ Les positions doivent être des nombres valides.",
        "play_too_many": "❌ Vous ne pouvez aligner que trois tuiles par tour.",
        "play_invalid_parameters": "❌ Paramètres invalides pour la commande `{prefix}joue`.",
        "play_no_indices": "❌ Indiquez au moins une tuile à utiliser.",
        "play_empty_hand": "❌ Votre main est vide. Utilisez `{prefix}pioche` pour récupérer des tuiles.",
        "play_out_of_range": "❌ L'une des positions demandées n'existe pas dans votre main actuelle.",
        "play_duplicate_index": "❌ Chaque position ne peut être utilisée qu'une seule fois par commande.",
        "play_generic_error": "❌ Impossible d'utiliser ces tuiles pour le moment.",
        "play_embed_title": "⚔️ Tuiles alignées",
        "field_resolution": "Résolution",
        "field_remaining_hand": "Main restante",
        "footer_draw_prompt": "Utilisez `{prefix}pioche` pour compléter votre main jusqu'à cinq tuiles.",
        "play_deck_empty_footer": "Le paquet est désormais vide. Pensez à `{prefix}resetDeck` si une nouvelle manche débute.",
        "reset_not_allowed": "⛔ Cette action est réservée aux administrateurs autorisés.",
        "reset_self": "🆕 Votre paquet a été reconstitué et mélangé. Utilisez `{prefix}pioche` pour récupérer une main de cinq tuiles.",
        "reset_other": "🆕 Le paquet de {mention} a été reconstitué et mélangé. Invitez-le à utiliser `{prefix}pioche` pour reformer sa main.",
        "reset_dm": "🃏 Votre paquet de tuiles a été réinitialisé par {actor}.",
    },
    "de": {
        "not_available": "❌ Dieser Befehl ist auf diesem Server nicht verfügbar.",
        "draw_invalid_count": "❌ Die Anzahl der Karten muss größer als 0 sein.",
        "draw_multiple_counts": "❌ Du kannst nur eine Anzahl an Karten zum Ziehen angeben.",
        "draw_unexpected_argument": "❌ Unbekanntes Argument. Verwende `{prefix}pioche [Anzahl] [--priv]` (z. B. `{prefix}pioche 3 --priv`).",
        "deck_empty_config": "❌ Das konfigurierte Deck ist leer. Überprüfe die Karteneinstellungen.",
        "draw_embed_title": "🪄 Karten ziehen",
        "auto_reset_footer": "Ein neues Deck wurde erstellt und gemischt.",
        "field_tiles": "Karten",
        "default_card_name": "Karte",
        "draw_deck_empty": "Das Deck ist leer, keine Karten zum Ziehen.",
        "draw_none": "Es konnte keine Karte gezogen werden.",
        "draw_hand_full": "Deine Hand ist bereits voll (5 Karten).",
        "draw_deck_not_enough": "Im Deck sind nicht genug Karten, um deine Hand zu füllen.",
        "field_hand": "Aktuelle Hand",
        "hand_empty": "(keine Karten auf der Hand)",
        "field_remaining": "Verbleibende Karten",
        "field_discard": "Abgeworfene Karten",
        "field_turn_action": "Aktion in diesem Zug",
        "turn_action_value": "Verwende `{prefix}joue <Positionen>`, um bis zu drei Karten auszuspielen (z. B. `{prefix}joue 1 3`).",
        "draw_deck_empty_footer": "Das Deck ist leer. Falls der Kampf weitergeht, nutze `{prefix}resetDeck`, um neu zu beginnen.",
        "dm_failed": "⚠️ Private Nachricht konnte nicht gesendet werden. Bitte erlaube Server-DMs.",
        "dm_sent": "📬 Ergebnis per privater Nachricht gesendet.",
        "play_missing_indices": "❌ Gib die Positionen der Karten an (z. B. `{prefix}joue 1 2`).",
        "play_invalid_index": "❌ Die Positionen müssen gültige Zahlen sein.",
        "play_too_many": "❌ Du kannst pro Zug nur drei Karten ausspielen.",
        "play_invalid_parameters": "❌ Ungültige Parameter für den Befehl `{prefix}joue`.",
        "play_no_indices": "❌ Gib mindestens eine Karte an, die du ausspielen möchtest.",
        "play_empty_hand": "❌ Deine Hand ist leer. Verwende `{prefix}pioche`, um Karten zu ziehen.",
        "play_out_of_range": "❌ Eine der angegebenen Positionen existiert nicht in deiner aktuellen Hand.",
        "play_duplicate_index": "❌ Jede Position kann pro Befehl nur einmal genutzt werden.",
        "play_generic_error": "❌ Diese Karten können derzeit nicht genutzt werden.",
        "play_embed_title": "⚔️ Ausgespielte Karten",
        "field_resolution": "Auflösung",
        "field_remaining_hand": "Verbleibende Hand",
        "footer_draw_prompt": "Verwende `{prefix}pioche`, um deine Hand wieder auf fünf Karten zu füllen.",
        "play_deck_empty_footer": "Das Deck ist jetzt leer. Erwäge `{prefix}resetDeck`, wenn eine neue Runde beginnt.",
        "reset_not_allowed": "⛔ Diese Aktion ist nur für autorisierte Administratoren.",
        "reset_self": "🆕 Dein Deck wurde neu aufgebaut und gemischt. Verwende `{prefix}pioche`, um wieder fünf Karten zu ziehen.",
        "reset_other": "🆕 Das Deck von {mention} wurde neu aufgebaut und gemischt. Bitte sie, `{prefix}pioche` zu verwenden, um ihre Hand neu zu bilden.",
        "reset_dm": "🃏 Dein Kartendeck wurde von {actor} zurückgesetzt.",
    },
    "es": {
        "not_available": "❌ Este comando no está disponible en este servidor.",
        "draw_invalid_count": "❌ El número de cartas debe ser mayor que 0.",
        "draw_multiple_counts": "❌ Solo puedes especificar un número de cartas para robar.",
        "draw_unexpected_argument": "❌ Argumento desconocido. Usa `{prefix}pioche [número] [--priv]` (ej. `{prefix}pioche 3 --priv`).",
        "deck_empty_config": "❌ El mazo configurado está vacío. Revisa la configuración de las fichas.",
        "draw_embed_title": "🪄 Robar cartas",
        "auto_reset_footer": "Se ha construido y barajado un nuevo mazo.",
        "field_tiles": "Cartas",
        "default_card_name": "Carta",
        "draw_deck_empty": "El mazo está vacío, no hay cartas para robar.",
        "draw_none": "No se pudo robar ninguna carta.",
        "draw_hand_full": "Tu mano ya está completa (5 cartas).",
        "draw_deck_not_enough": "El mazo no tiene suficientes cartas para completar tu mano.",
        "field_hand": "Mano actual",
        "hand_empty": "(sin cartas en mano)",
        "field_remaining": "Cartas restantes",
        "field_discard": "Cartas descartadas",
        "field_turn_action": "Acción del turno",
        "turn_action_value": "Usa `{prefix}joue <índices>` para alinear hasta tres cartas (ej. `{prefix}joue 1 3`).",
        "draw_deck_empty_footer": "El mazo está vacío. Si el enfrentamiento continúa, usa `{prefix}resetDeck` para reiniciar.",
        "dm_failed": "⚠️ No se pudo enviar un mensaje privado. Permite los MD del servidor.",
        "dm_sent": "📬 Resultado enviado por mensaje privado.",
        "play_missing_indices": "❌ Indica las posiciones de las cartas a usar (ej. `{prefix}joue 1 2`).",
        "play_invalid_index": "❌ Las posiciones deben ser números válidos.",
        "play_too_many": "❌ Solo puedes alinear tres cartas por turno.",
        "play_invalid_parameters": "❌ Parámetros no válidos para el comando `{prefix}joue`.",
        "play_no_indices": "❌ Indica al menos una carta para usar.",
        "play_empty_hand": "❌ Tu mano está vacía. Usa `{prefix}pioche` para robar cartas.",
        "play_out_of_range": "❌ Una de las posiciones solicitadas no existe en tu mano actual.",
        "play_duplicate_index": "❌ Cada posición solo puede usarse una vez por comando.",
        "play_generic_error": "❌ No es posible usar estas cartas por el momento.",
        "play_embed_title": "⚔️ Cartas alineadas",
        "field_resolution": "Resolución",
        "field_remaining_hand": "Mano restante",
        "footer_draw_prompt": "Usa `{prefix}pioche` para rellenar tu mano hasta cinco cartas.",
        "play_deck_empty_footer": "El mazo ahora está vacío. Considera `{prefix}resetDeck` si empieza una nueva ronda.",
        "reset_not_allowed": "⛔ Esta acción está reservada para administradores autorizados.",
        "reset_self": "🆕 Tu mazo ha sido reconstruido y barajado. Usa `{prefix}pioche` para obtener una mano de cinco cartas.",
        "reset_other": "🆕 El mazo de {mention} ha sido reconstruido y barajado. Invítale a usar `{prefix}pioche` para rehacer su mano.",
        "reset_dm": "🃏 Tu mazo de cartas fue restablecido por {actor}.",
    },
}


class DeckManager:
    """Utility class to manage per-user decks stored in the global CACHE."""

    _lock = asyncio.Lock()

    @staticmethod
    def _get_config() -> Dict:
        return CACHE.get("card_config", {}) or {}

    @classmethod
    def get_allowed_server_id(cls) -> Optional[str]:
        allowed = cls._get_config().get("allowed_server_id")
        if allowed is None:
            return None
        return str(allowed)

    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        config = cls._get_config()
        admin_ids = config.get("admin_users", []) or []
        return str(user_id) in {str(admin_id) for admin_id in admin_ids}

    @classmethod
    def _get_card_map(cls) -> Dict[str, Dict]:
        cards = cls._get_config().get("cards", []) or []
        return {card.get("id"): card for card in cards if card.get("id")}

    @classmethod
    def _get_deck_spec_for_user(cls, user_id: int) -> List[Dict]:
        config = cls._get_config()
        user_decks = config.get("user_decks", {}) or {}
        deck_spec = user_decks.get(str(user_id))
        if not deck_spec:
            deck_spec = config.get("default_deck", []) or []
        return deck_spec

    @classmethod
    def _build_deck(cls, user_id: int) -> List[str]:
        card_map = cls._get_card_map()
        deck_spec = cls._get_deck_spec_for_user(user_id)
        deck: List[str] = []

        for entry in deck_spec:
            card_id = entry.get("card_id")
            count = entry.get("count", 0)
            if not card_id or count <= 0:
                continue
            if card_id not in card_map:
                audit_logger.warning(
                    f"Card '{card_id}' referenced in deck for user {user_id} is not defined in cards list."
                )
                continue
            deck.extend([card_id] * int(count))

        random.shuffle(deck)
        return deck

    @classmethod
    def _get_guild_state(cls, guild_id: int) -> Dict[str, Dict[str, List[str]]]:
        guild_states = CACHE.setdefault("card_states", {})
        return guild_states.setdefault(str(guild_id), {})

    @classmethod
    def _ensure_state(cls, guild_id: int, user_id: int) -> Dict[str, List[str]]:
        states = cls._get_guild_state(guild_id)
        state = states.get(str(user_id))

        if isinstance(state, list):
            # Legacy format: only the deck list was stored.
            state = {"deck": state, "hand": [], "discard": []}
        elif state is None or not isinstance(state, dict):
            state = {"deck": [], "hand": [], "discard": []}

        state.setdefault("deck", [])
        state.setdefault("hand", [])
        state.setdefault("discard", [])

        states[str(user_id)] = state
        return state

    @classmethod
    def reset_deck(cls, guild_id: int, user_id: int) -> Tuple[Dict[str, List[str]], bool]:
        """Reset the deck and clear the current hand/discard for the given user."""

        deck = cls._build_deck(user_id)
        states = cls._get_guild_state(guild_id)
        state = {"deck": deck, "hand": [], "discard": []}
        states[str(user_id)] = state
        return state, bool(deck)

    @classmethod
    def draw_hand(
        cls,
        guild_id: int,
        user_id: int,
        count: Optional[int] = None,
    ) -> Tuple[List[str], List[str], bool, bool, Dict[str, List[str]]]:
        """Draw tiles until the player's hand reaches five cards, when possible.
        
        Args:
            guild_id: The guild ID
            user_id: The user ID
            count: Optional number of cards to draw. If None, fills hand to 5 cards.
        """

        state = cls._ensure_state(guild_id, user_id)
        auto_reset = False

        if not state["deck"] and not state["hand"]:
            if state["discard"]:
                # Deck exhausted – no automatic reset.
                return [], list(state["hand"]), False, True, state

            state["deck"] = cls._build_deck(user_id)
            state["discard"] = []
            auto_reset = True

            if not state["deck"]:
                return [], list(state["hand"]), auto_reset, True, state

        # Determine how many cards to draw
        if count is not None:
            # Draw exact count requested (up to deck size)
            draw_count = min(count, len(state["deck"]))
        else:
            # Original behavior: fill hand to 5 cards
            space_in_hand = max(0, 5 - len(state["hand"]))
            draw_count = min(space_in_hand, len(state["deck"]))
        
        drawn_cards: List[str] = []

        for _ in range(draw_count):
            drawn_cards.append(state["deck"].pop())

        state["hand"].extend(drawn_cards)
        deck_empty_after = len(state["deck"]) == 0

        return drawn_cards, list(state["hand"]), auto_reset, deck_empty_after, state

    @classmethod
    def play_cards_by_indices(
        cls,
        guild_id: int,
        user_id: int,
        indices: List[int],
    ) -> Tuple[List[str], List[str], bool, Dict[str, List[str]]]:
        """Remove up to three tiles from the player's hand based on their position."""

        if not indices:
            raise ValueError("no_indices")
        if len(indices) > 3:
            raise ValueError("too_many")

        state = cls._ensure_state(guild_id, user_id)
        hand = state["hand"]

        if not hand:
            raise ValueError("empty_hand")

        unique_order: List[int] = []
        seen: Set[int] = set()
        for raw_index in indices:
            try:
                index_value = int(raw_index)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid_index") from exc

            if index_value < 1 or index_value > len(hand):
                raise ValueError("out_of_range")
            if index_value in seen:
                raise ValueError("duplicate_index")
            seen.add(index_value)
            unique_order.append(index_value)

        extracted: List[Tuple[int, str]] = []
        for index_value in sorted(unique_order, reverse=True):
            card_id = hand.pop(index_value - 1)
            extracted.append((index_value, card_id))

        extracted.sort(key=lambda pair: unique_order.index(pair[0]))
        played_cards = [card_id for _, card_id in extracted]
        state["discard"].extend(played_cards)
        deck_empty_after = len(state["deck"]) == 0

        return played_cards, list(state["hand"]), deck_empty_after, state

    @classmethod
    def get_remaining_cards(cls, guild_id: int, user_id: int) -> int:
        state = cls._ensure_state(guild_id, user_id)
        return len(state["deck"])

    @classmethod
    def get_hand(cls, guild_id: int, user_id: int) -> List[str]:
        state = cls._ensure_state(guild_id, user_id)
        return list(state["hand"])

    @classmethod
    def get_card_info(cls, card_id: str) -> Dict:
        return cls._get_card_map().get(card_id, {"id": card_id, "name": card_id})


class CardDraws(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _get_translations(ctx: commands.Context) -> Dict[str, str]:
        lang = "en"
        if ctx.guild is not None:
            lang = get_server_language(ctx.guild.id)
        return CARD_TRANSLATIONS.get(lang, CARD_TRANSLATIONS["en"])

    @staticmethod
    def _get_prefix(ctx: commands.Context) -> str:
        prefix = (getattr(ctx, "clean_prefix", None) or getattr(ctx, "prefix", None) or "").strip()
        if prefix:
            return prefix
        if ctx.guild is not None:
            guild_prefs = CACHE.get("server_prefs", {}).get(str(ctx.guild.id), {})
            stored_prefix = guild_prefs.get("prefix")
            if stored_prefix:
                return stored_prefix
        return config.get("prefix", "!")

    @staticmethod
    def _is_server_allowed(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False
        allowed_server_id = DeckManager.get_allowed_server_id()
        if allowed_server_id in (None, "0", ""):
            return True
        return str(ctx.guild.id) == allowed_server_id

    @staticmethod
    def _parse_draw_flags(args: Tuple[str, ...]) -> Tuple[Optional[int], bool]:
        private = False
        count = None

        for arg in args:
            normalized = arg.lower()
            if normalized in {"--priv", "--private"}:
                private = True
                continue
            
            # Try to parse as a number
            try:
                num = int(arg)
                if num < 1:
                    raise ValueError("invalid_count")
                if count is not None:
                    raise ValueError("multiple_counts")
                count = num
                continue
            except ValueError as exc:
                if str(exc) in {"invalid_count", "multiple_counts"}:
                    raise
                # Not a number and not --priv, so it's unexpected
                raise ValueError("unexpected_argument")

        return count, private

    @staticmethod
    def _parse_play_arguments(args: Tuple[str, ...]) -> Tuple[List[int], bool]:
        private = False
        indices: List[int] = []

        for arg in args:
            normalized = arg.lower()
            if normalized in {"--priv", "--private"}:
                private = True
                continue

            try:
                index_value = int(arg)
            except ValueError as exc:
                raise ValueError("invalid_index") from exc

            indices.append(index_value)

        if not indices:
            raise ValueError("no_indices")
        if len(indices) > 3:
            raise ValueError("too_many")

        return indices, private

    @commands.command(name="pioche", aliases=["p"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def draw_cards(self, ctx: commands.Context, *args: str):
        """Draw tiles to fill the player's hand up to five cards."""

        tr = self._get_translations(ctx)
        prefix = self._get_prefix(ctx)

        if not self._is_server_allowed(ctx):
            await ctx.send(tr["not_available"])
            return

        try:
            count, private = self._parse_draw_flags(args)
        except ValueError as exc:
            error_code = str(exc)
            if error_code == "invalid_count":
                await ctx.send(tr["draw_invalid_count"])
            elif error_code == "multiple_counts":
                await ctx.send(tr["draw_multiple_counts"])
            else:
                await ctx.send(tr["draw_unexpected_argument"].format(prefix=prefix))
            return

        async with DeckManager._lock:
            drawn_cards, hand_snapshot, auto_reset, deck_empty_after, state = DeckManager.draw_hand(
                ctx.guild.id, ctx.author.id, count
            )

        if not drawn_cards and not hand_snapshot and not state.get("deck") and not state.get("discard"):
            await ctx.send(tr["deck_empty_config"])
            return

        embed = discord.Embed(title=tr["draw_embed_title"], color=discord.Color.blurple())
        footer_messages: List[str] = []

        if auto_reset:
            footer_messages.append(tr["auto_reset_footer"])

        if drawn_cards:
            draw_lines = []
            for card_id in drawn_cards:
                card = DeckManager.get_card_info(card_id)
                name = card.get("name", card.get("id", tr["default_card_name"]))
                description = card.get("description")
                if description:
                    draw_lines.append(f"- **{name}** — {description}")
                else:
                    draw_lines.append(f"- **{name}**")
            embed.add_field(name=tr["field_tiles"], value="\n".join(draw_lines), inline=False)
        else:
            # No cards were drawn
            if count is not None:
                # Specific count was requested but nothing drawn
                if deck_empty_after or len(state.get("deck", [])) == 0:
                    footer_messages.append(tr["draw_deck_empty"])
                else:
                    footer_messages.append(tr["draw_none"])
            elif len(hand_snapshot) >= 5:
                footer_messages.append(tr["draw_hand_full"])
            elif deck_empty_after:
                footer_messages.append(tr["draw_deck_not_enough"])

        if hand_snapshot:
            hand_lines = []
            for index, card_id in enumerate(hand_snapshot, start=1):
                card = DeckManager.get_card_info(card_id)
                hand_lines.append(f"{index}. {card.get('name', card.get('id', tr['default_card_name']))}")
            embed.add_field(name=tr["field_hand"], value="\n".join(hand_lines), inline=False)
        else:
            embed.add_field(name=tr["field_hand"], value=tr["hand_empty"], inline=False)

        deck_remaining = len(state.get("deck", []))
        discard_count = len(state.get("discard", []))
        embed.add_field(name=tr["field_remaining"], value=str(deck_remaining), inline=True)
        embed.add_field(name=tr["field_discard"], value=str(discard_count), inline=True)

        if hand_snapshot:
            embed.add_field(
                name=tr["field_turn_action"],
                value=tr["turn_action_value"].format(prefix=prefix),
                inline=False,
            )

        if deck_empty_after and deck_remaining == 0:
            footer_messages.append(tr["draw_deck_empty_footer"].format(prefix=prefix))

        if footer_messages:
            embed.set_footer(text=" ".join(footer_messages))

        if private:
            try:
                await ctx.author.send(embed=embed)
            except discord.Forbidden:
                await ctx.send(tr["dm_failed"])
                return

            await ctx.send(tr["dm_sent"])
        else:
            await ctx.send(embed=embed)

    @commands.command(name="joue", aliases=["playtiles", "playtile"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def play_tiles(self, ctx: commands.Context, *args: str):
        """Play up to three tiles from the current hand using their displayed indices."""

        tr = self._get_translations(ctx)
        prefix = self._get_prefix(ctx)

        if not self._is_server_allowed(ctx):
            await ctx.send(tr["not_available"])
            return

        try:
            indices, private = self._parse_play_arguments(args)
        except ValueError as exc:
            error_code = str(exc)
            if error_code == "no_indices":
                await ctx.send(tr["play_missing_indices"].format(prefix=prefix))
            elif error_code == "invalid_index":
                await ctx.send(tr["play_invalid_index"])
            elif error_code == "too_many":
                await ctx.send(tr["play_too_many"])
            else:
                await ctx.send(tr["play_invalid_parameters"].format(prefix=prefix))
            return

        async with DeckManager._lock:
            try:
                played_cards, hand_snapshot, deck_empty_after, state = DeckManager.play_cards_by_indices(
                    ctx.guild.id, ctx.author.id, indices
                )
            except ValueError as exc:
                error_code = str(exc)
                if error_code == "no_indices":
                    await ctx.send(tr["play_no_indices"])
                elif error_code == "too_many":
                    await ctx.send(tr["play_too_many"])
                elif error_code == "empty_hand":
                    await ctx.send(tr["play_empty_hand"].format(prefix=prefix))
                elif error_code == "out_of_range":
                    await ctx.send(tr["play_out_of_range"])
                elif error_code == "duplicate_index":
                    await ctx.send(tr["play_duplicate_index"])
                else:
                    await ctx.send(tr["play_generic_error"])
                return

        card_details = [DeckManager.get_card_info(card_id) for card_id in played_cards]
        lines = []
        for card in card_details:
            name = card.get("name", card.get("id", tr["default_card_name"]))
            description = card.get("description")
            if description:
                lines.append(f"- **{name}** — {description}")
            else:
                lines.append(f"- **{name}**")

        embed = discord.Embed(title=tr["play_embed_title"], color=discord.Color.orange())
        embed.add_field(name=tr["field_resolution"], value="\n".join(lines), inline=False)

        if hand_snapshot:
            hand_lines = []
            for index, card_id in enumerate(hand_snapshot, start=1):
                card = DeckManager.get_card_info(card_id)
                hand_lines.append(f"{index}. {card.get('name', card.get('id', tr['default_card_name']))}")
            embed.add_field(name=tr["field_remaining_hand"], value="\n".join(hand_lines), inline=False)
        else:
            embed.add_field(name=tr["field_remaining_hand"], value=tr["hand_empty"], inline=False)

        deck_remaining = len(state.get("deck", []))
        discard_count = len(state.get("discard", []))
        embed.add_field(name=tr["field_remaining"], value=str(deck_remaining), inline=True)
        embed.add_field(name=tr["field_discard"], value=str(discard_count), inline=True)

        footer_messages: List[str] = [tr["footer_draw_prompt"].format(prefix=prefix)]
        if deck_empty_after and deck_remaining == 0:
            footer_messages.append(tr["play_deck_empty_footer"].format(prefix=prefix))

        embed.set_footer(text=" ".join(footer_messages))

        if private:
            try:
                await ctx.author.send(embed=embed)
            except discord.Forbidden:
                await ctx.send(tr["dm_failed"])
                return

            await ctx.send(tr["dm_sent"])
        else:
            await ctx.send(embed=embed)

    @commands.command(name="resetDeck", aliases=["rd"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def reset_deck(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Reset a deck (self or another user if admin)."""

        tr = self._get_translations(ctx)
        prefix = self._get_prefix(ctx)

        if not self._is_server_allowed(ctx):
            await ctx.send(tr["not_available"])
            return

        target = member or ctx.author
        acting_user_is_admin = DeckManager.is_admin(ctx.author.id)

        if member and not acting_user_is_admin:
            await ctx.send(tr["reset_not_allowed"])
            return

        async with DeckManager._lock:
            _, has_cards = DeckManager.reset_deck(ctx.guild.id, target.id)

        if not has_cards:
            await ctx.send(tr["deck_empty_config"])
            return

        if target == ctx.author:
            await ctx.send(tr["reset_self"].format(prefix=prefix))
        else:
            await ctx.send(tr["reset_other"].format(mention=target.mention, prefix=prefix))
            try:
                await target.send(tr["reset_dm"].format(actor=ctx.author.display_name))
            except discord.Forbidden:
                pass
def setup(bot: commands.Bot):
    cog = CardDraws(bot)
    maybe_coro = bot.add_cog(cog)
    if asyncio.iscoroutine(maybe_coro):
        bot.loop.create_task(maybe_coro)
