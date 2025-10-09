import asyncio
import random
from typing import Dict, List, Optional, Tuple

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
    def _get_guild_state(cls, guild_id: int) -> Dict[str, List[str]]:
        guild_states = CACHE.setdefault("card_states", {})
        return guild_states.setdefault(str(guild_id), {})

    @classmethod
    def reset_deck(cls, guild_id: int, user_id: int) -> Tuple[List[str], bool]:
        """Reset the deck for the given user. Returns the deck and a boolean indicating success."""
        deck = cls._build_deck(user_id)
        states = cls._get_guild_state(guild_id)
        states[str(user_id)] = deck
        return deck, bool(deck)

    @classmethod
    def draw_cards(
        cls,
        guild_id: int,
        user_id: int,
        requested_count: int,
    ) -> Tuple[List[str], bool, bool, bool]:
        """
        Draw cards from the user's deck.

        Returns a tuple of:
            (drawn_cards, auto_reset, partial_draw, deck_empty_after)
        """

        states = cls._get_guild_state(guild_id)
        deck = states.get(str(user_id))
        auto_reset = False

        if not deck:
            deck, has_cards = cls.reset_deck(guild_id, user_id)
            auto_reset = True
            if not has_cards:
                return [], auto_reset, False, True

        available_before = len(deck)
        draw_count = min(requested_count, available_before)

        drawn_cards = [deck.pop() for _ in range(draw_count)]
        deck_empty_after = len(deck) == 0
        partial_draw = draw_count < requested_count

        return drawn_cards, auto_reset, partial_draw, deck_empty_after

    @classmethod
    def get_remaining_cards(cls, guild_id: int, user_id: int) -> int:
        states = cls._get_guild_state(guild_id)
        deck = states.get(str(user_id), [])
        return len(deck)

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
    def _parse_arguments(args: Tuple[str, ...]) -> Tuple[int, bool]:
        count: Optional[int] = None
        private = False

        for arg in args:
            normalized = arg.lower()
            if normalized in {"--priv", "--private"}:
                private = True
                continue

            if count is None:
                try:
                    count = int(arg)
                except ValueError as exc:
                    raise ValueError("invalid_number") from exc
            else:
                raise ValueError("too_many_args")

        if count is None:
            count = 1

        if count <= 0:
            raise ValueError("non_positive")

        return count, private

    @commands.command(name="pioche", aliases=["p"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def draw_cards(self, ctx: commands.Context, *args: str):
        """Draw one or multiple cards from the caller's personal deck."""

        if not self._is_server_allowed(ctx):
            await ctx.send("❌ Cette commande n'est pas disponible sur ce serveur.")
            return

        try:
            count, private = self._parse_arguments(args)
        except ValueError as exc:
            error_code = str(exc)
            if error_code == "invalid_number":
                await ctx.send("❌ Veuillez indiquer un nombre valide de cartes à piocher.")
            elif error_code == "too_many_args":
                await ctx.send("❌ Trop d'arguments fournis. Exemple : `!pioche 3 --priv`.")
            else:
                await ctx.send("❌ Le nombre de cartes doit être strictement positif.")
            return

        async with DeckManager._lock:
            drawn_cards, auto_reset, partial_draw, deck_empty_after = DeckManager.draw_cards(
                ctx.guild.id, ctx.author.id, count
            )

        if not drawn_cards:
            await ctx.send("❌ Aucune carte n'a pu être piochée. Vérifiez la configuration du paquet.")
            return

        card_details = [DeckManager.get_card_info(card_id) for card_id in drawn_cards]
        description_lines = [f"- {card.get('name', card.get('id', 'Carte'))}" for card in card_details]
        description = "\n".join(description_lines)

        title = "🃏 Résultat de la pioche"
        footer_messages: List[str] = []

        if auto_reset:
            footer_messages.append("Le paquet était vide et a été reconstitué automatiquement.")
        if partial_draw:
            footer_messages.append("Le paquet ne contenait pas assez de cartes pour ce tirage.")
        if deck_empty_after:
            footer_messages.append("Le paquet est maintenant vide.")

        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())

        if len(card_details) == 1:
            card = card_details[0]
            image_url = card.get("image")
            if image_url:
                embed.set_thumbnail(url=image_url)
            if card.get("description"):
                embed.add_field(name="Description", value=card["description"], inline=False)

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
            deck, has_cards = DeckManager.reset_deck(ctx.guild.id, target.id)

        if not has_cards:
            await ctx.send("❌ Le paquet configuré est vide. Vérifiez la configuration des cartes.")
            return

        if target == ctx.author:
            await ctx.send("🆕 Votre paquet a été reconstitué et mélangé.")
        else:
            await ctx.send(f"🆕 Le paquet de {target.mention} a été reconstitué et mélangé.")
            try:
                await target.send(
                    f"🃏 Votre paquet de cartes a été réinitialisé par {ctx.author.display_name}."
                )
            except discord.Forbidden:
                pass
def setup(bot: commands.Bot):
    bot.add_cog(CardDraws(bot))
