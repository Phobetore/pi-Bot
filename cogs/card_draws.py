import asyncio
import random
from typing import Dict, List, Optional, Set, Tuple

import discord
from discord.ext import commands

from main import CACHE, audit_logger


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
    ) -> Tuple[List[str], List[str], bool, bool, Dict[str, List[str]]]:
        """Draw tiles until the player's hand reaches five cards, when possible."""

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
    def _is_server_allowed(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False
        allowed_server_id = DeckManager.get_allowed_server_id()
        if allowed_server_id in (None, "0", ""):
            return True
        return str(ctx.guild.id) == allowed_server_id

    @staticmethod
    def _parse_draw_flags(args: Tuple[str, ...]) -> bool:
        private = False

        for arg in args:
            normalized = arg.lower()
            if normalized in {"--priv", "--private"}:
                private = True
                continue
            raise ValueError("unexpected_argument")

        return private

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

        if not self._is_server_allowed(ctx):
            await ctx.send("❌ Cette commande n'est pas disponible sur ce serveur.")
            return

        try:
            private = self._parse_draw_flags(args)
        except ValueError:
            await ctx.send("❌ Argument inconnu. Utilisez uniquement `--priv` pour recevoir le résultat en message privé.")
            return

        async with DeckManager._lock:
            drawn_cards, hand_snapshot, auto_reset, deck_empty_after, state = DeckManager.draw_hand(
                ctx.guild.id, ctx.author.id
            )

        if not drawn_cards and not hand_snapshot and not state.get("deck") and not state.get("discard"):
            await ctx.send("❌ Le paquet configuré est vide. Vérifiez la configuration des tuiles.")
            return

        embed = discord.Embed(title="🪄 Pioche des Tuiles", color=discord.Color.blurple())
        footer_messages: List[str] = []

        if auto_reset:
            footer_messages.append("Un nouveau paquet a été constitué et mélangé.")

        if drawn_cards:
            draw_lines = []
            for card_id in drawn_cards:
                card = DeckManager.get_card_info(card_id)
                name = card.get("name", card.get("id", "Tuile"))
                description = card.get("description")
                if description:
                    draw_lines.append(f"- **{name}** — {description}")
                else:
                    draw_lines.append(f"- **{name}**")
            embed.add_field(name="Tuiles", value="\n".join(draw_lines), inline=False)
        elif len(hand_snapshot) >= 5:
            footer_messages.append("Votre main est déjà complète (5 tuiles).")
        elif deck_empty_after:
            footer_messages.append("Le paquet ne contient plus assez de tuiles pour compléter votre main.")

        if hand_snapshot:
            hand_lines = []
            for index, card_id in enumerate(hand_snapshot, start=1):
                card = DeckManager.get_card_info(card_id)
                hand_lines.append(f"{index}. {card.get('name', card.get('id', 'Tuile'))}")
            embed.add_field(name="Main actuelle", value="\n".join(hand_lines), inline=False)
        else:
            embed.add_field(name="Main actuelle", value="(aucune tuile en main)", inline=False)

        deck_remaining = len(state.get("deck", []))
        discard_count = len(state.get("discard", []))
        embed.add_field(name="Tuiles restantes", value=str(deck_remaining), inline=True)
        embed.add_field(name="Tuiles défaussées", value=str(discard_count), inline=True)

        if hand_snapshot:
            embed.add_field(
                name="Action du tour",
                value="Utilisez `!joue <indices>` pour aligner jusqu'à trois tuiles (ex. `!joue 1 3`).",
                inline=False,
            )

        if deck_empty_after and deck_remaining == 0:
            footer_messages.append("Le paquet est vide. Si l'affrontement continue, utilisez `!resetDeck` pour recommencer.")

        if footer_messages:
            embed.set_footer(text=" ".join(footer_messages))

        if private:
            try:
                await ctx.author.send(embed=embed)
            except discord.Forbidden:
                await ctx.send("⚠️ Impossible d'envoyer un message privé. Merci d'autoriser les DM du serveur.")
                return

            await ctx.send("📬 Résultat envoyé en message privé.")
        else:
            await ctx.send(embed=embed)

    @commands.command(name="joue", aliases=["playtiles", "playtile"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def play_tiles(self, ctx: commands.Context, *args: str):
        """Play up to three tiles from the current hand using their displayed indices."""

        if not self._is_server_allowed(ctx):
            await ctx.send("❌ Cette commande n'est pas disponible sur ce serveur.")
            return

        try:
            indices, private = self._parse_play_arguments(args)
        except ValueError as exc:
            error_code = str(exc)
            if error_code == "no_indices":
                await ctx.send("❌ Indiquez les positions des tuiles à utiliser (ex. `!joue 1 2`).")
            elif error_code == "invalid_index":
                await ctx.send("❌ Les positions doivent être des nombres valides.")
            elif error_code == "too_many":
                await ctx.send("❌ Vous ne pouvez aligner que trois tuiles par tour.")
            else:
                await ctx.send("❌ Paramètres invalides pour la commande `!joue`.")
            return

        async with DeckManager._lock:
            try:
                played_cards, hand_snapshot, deck_empty_after, state = DeckManager.play_cards_by_indices(
                    ctx.guild.id, ctx.author.id, indices
                )
            except ValueError as exc:
                error_code = str(exc)
                if error_code == "no_indices":
                    await ctx.send("❌ Indiquez au moins une tuile à utiliser.")
                elif error_code == "too_many":
                    await ctx.send("❌ Vous ne pouvez aligner que trois tuiles par tour.")
                elif error_code == "empty_hand":
                    await ctx.send("❌ Votre main est vide. Utilisez `!pioche` pour récupérer des tuiles.")
                elif error_code == "out_of_range":
                    await ctx.send("❌ L'une des positions demandées n'existe pas dans votre main actuelle.")
                elif error_code == "duplicate_index":
                    await ctx.send("❌ Chaque position ne peut être utilisée qu'une seule fois par commande.")
                else:
                    await ctx.send("❌ Impossible d'utiliser ces tuiles pour le moment.")
                return

        card_details = [DeckManager.get_card_info(card_id) for card_id in played_cards]
        lines = []
        for card in card_details:
            name = card.get("name", card.get("id", "Tuile"))
            description = card.get("description")
            if description:
                lines.append(f"- **{name}** — {description}")
            else:
                lines.append(f"- **{name}**")

        embed = discord.Embed(title="⚔️ Tuiles alignées", color=discord.Color.orange())
        embed.add_field(name="Résolution", value="\n".join(lines), inline=False)

        if hand_snapshot:
            hand_lines = []
            for index, card_id in enumerate(hand_snapshot, start=1):
                card = DeckManager.get_card_info(card_id)
                hand_lines.append(f"{index}. {card.get('name', card.get('id', 'Tuile'))}")
            embed.add_field(name="Main restante", value="\n".join(hand_lines), inline=False)
        else:
            embed.add_field(name="Main restante", value="(aucune tuile en main)", inline=False)

        deck_remaining = len(state.get("deck", []))
        discard_count = len(state.get("discard", []))
        embed.add_field(name="Tuiles restantes", value=str(deck_remaining), inline=True)
        embed.add_field(name="Tuiles défaussées", value=str(discard_count), inline=True)

        footer_messages: List[str] = ["Utilisez `!pioche` pour compléter votre main jusqu'à cinq tuiles."]
        if deck_empty_after and deck_remaining == 0:
            footer_messages.append("Le paquet est désormais vide. Pensez à `!resetDeck` si une nouvelle manche débute.")

        embed.set_footer(text=" ".join(footer_messages))

        if private:
            try:
                await ctx.author.send(embed=embed)
            except discord.Forbidden:
                await ctx.send("⚠️ Impossible d'envoyer un message privé. Merci d'autoriser les DM du serveur.")
                return

            await ctx.send("📬 Résultat envoyé en message privé.")
        else:
            await ctx.send(embed=embed)

    @commands.command(name="resetDeck", aliases=["rd"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def reset_deck(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Reset a deck (self or another user if admin)."""

        if not self._is_server_allowed(ctx):
            await ctx.send("❌ Cette commande n'est pas disponible sur ce serveur.")
            return

        target = member or ctx.author
        acting_user_is_admin = DeckManager.is_admin(ctx.author.id)

        if member and not acting_user_is_admin:
            await ctx.send("⛔ Cette action est réservée aux administrateurs autorisés.")
            return

        async with DeckManager._lock:
            _, has_cards = DeckManager.reset_deck(ctx.guild.id, target.id)

        if not has_cards:
            await ctx.send("❌ Le paquet configuré est vide. Vérifiez la configuration des tuiles.")
            return

        if target == ctx.author:
            await ctx.send(
                "🆕 Votre paquet a été reconstitué et mélangé. Utilisez `!pioche` pour récupérer une main de cinq tuiles."
            )
        else:
            await ctx.send(
                f"🆕 Le paquet de {target.mention} a été reconstitué et mélangé. Invitez-le à utiliser `!pioche` pour reformer sa main."
            )
            try:
                await target.send(
                    f"🃏 Votre paquet de tuiles a été réinitialisé par {ctx.author.display_name}."
                )
            except discord.Forbidden:
                pass
async def setup(bot: commands.Bot):
    await bot.add_cog(CardDraws(bot))
