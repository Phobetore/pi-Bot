import random
import discord
from discord.ext import commands
from typing import Optional, List, Dict
import asyncio

from main import CACHE, audit_logger, get_server_language, TRANSLATIONS


# ─────────────────────────────────────────────
#    Card Deck Management
# ─────────────────────────────────────────────
class CardDeck:
    """
    Represents a standard 52-card playing deck.
    """
    SUITS = ["♠️", "♥️", "♦️", "♣️"]
    RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    
    def __init__(self):
        self.cards = self._create_deck()
        self.drawn_cards = []
    
    def _create_deck(self) -> List[str]:
        """Create a standard 52-card deck."""
        return [f"{rank}{suit}" for suit in self.SUITS for rank in self.RANKS]
    
    def shuffle(self):
        """Shuffle the deck."""
        random.shuffle(self.cards)
        self.drawn_cards = []
    
    def draw(self, count: int = 1) -> List[str]:
        """Draw cards from the deck."""
        if count > len(self.cards):
            count = len(self.cards)
        
        drawn = []
        for _ in range(count):
            if self.cards:
                card = self.cards.pop(0)
                self.drawn_cards.append(card)
                drawn.append(card)
        return drawn
    
    def reset(self):
        """Reset the deck to a fresh shuffled state."""
        self.cards = self._create_deck()
        self.drawn_cards = []
        self.shuffle()
    
    def remaining_count(self) -> int:
        """Get the number of cards remaining in the deck."""
        return len(self.cards)
    
    def to_dict(self) -> dict:
        """Serialize the deck to a dictionary."""
        return {
            "cards": self.cards,
            "drawn_cards": self.drawn_cards
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Deserialize a deck from a dictionary."""
        deck = cls()
        deck.cards = data.get("cards", deck.cards)
        deck.drawn_cards = data.get("drawn_cards", [])
        return deck


# ─────────────────────────────────────────────
#    Cache Manager for Card Decks
# ─────────────────────────────────────────────
class CardDeckManager:
    """
    Manages card decks per server using the global cache.
    """
    _lock = asyncio.Lock()
    
    @staticmethod
    async def get_deck(guild_id: int) -> CardDeck:
        """Get or create a deck for a server."""
        async with CardDeckManager._lock:
            guild_str = str(guild_id)
            if guild_str not in CACHE["server_prefs"]:
                CACHE["server_prefs"][guild_str] = {}
            
            if "card_deck" not in CACHE["server_prefs"][guild_str]:
                deck = CardDeck()
                deck.shuffle()
                CACHE["server_prefs"][guild_str]["card_deck"] = deck.to_dict()
            
            return CardDeck.from_dict(CACHE["server_prefs"][guild_str]["card_deck"])
    
    @staticmethod
    async def save_deck(guild_id: int, deck: CardDeck):
        """Save a deck for a server."""
        async with CardDeckManager._lock:
            guild_str = str(guild_id)
            if guild_str not in CACHE["server_prefs"]:
                CACHE["server_prefs"][guild_str] = {}
            CACHE["server_prefs"][guild_str]["card_deck"] = deck.to_dict()


# ─────────────────────────────────────────────
#    Card Draw Cog
# ─────────────────────────────────────────────
class CardDraw(commands.Cog):
    """
    Cog for managing card drawing commands.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command(name="draw", aliases=["d"])
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def draw_card(self, ctx: commands.Context, count: int = 1):
        """
        Draw one or more cards from the server's deck.
        
        Usage:
            !draw       - Draw 1 card
            !draw 5     - Draw 5 cards
        """
        if not ctx.guild:
            await ctx.send("❌ This command can only be used in a server.")
            return
        
        if count < 1:
            await ctx.send("❌ You must draw at least 1 card.")
            return
        
        if count > 10:
            await ctx.send("❌ You can only draw up to 10 cards at once.")
            return
        
        # Get the server's deck
        deck = await CardDeckManager.get_deck(ctx.guild.id)
        
        # Check if enough cards remain
        if deck.remaining_count() == 0:
            await ctx.send("❌ The deck is empty! Use `!newdeck` or `!shuffle` to reset it.")
            return
        
        # Draw cards
        drawn_cards = deck.draw(count)
        
        # Save the updated deck
        await CardDeckManager.save_deck(ctx.guild.id, deck)
        
        # Create embed
        embed = discord.Embed(
            title="🃏 Cards Drawn",
            color=discord.Color.blue(),
            description=f"**{ctx.author.display_name}** drew {len(drawn_cards)} card(s):"
        )
        
        # Display drawn cards
        cards_display = " ".join(drawn_cards)
        embed.add_field(name="Cards", value=cards_display, inline=False)
        embed.add_field(name="Remaining in deck", value=f"{deck.remaining_count()} cards", inline=False)
        
        embed.set_footer(text=f"Drawn by {ctx.author.name}")
        
        await ctx.send(embed=embed)
        
        # Log the draw
        audit_logger.warning(f"User {ctx.author.id} drew {len(drawn_cards)} cards in guild {ctx.guild.id}")
    
    @commands.command(name="shuffle")
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def shuffle_deck(self, ctx: commands.Context):
        """
        Shuffle the server's deck, returning all drawn cards.
        
        Usage:
            !shuffle
        """
        if not ctx.guild:
            await ctx.send("❌ This command can only be used in a server.")
            return
        
        # Get the server's deck
        deck = await CardDeckManager.get_deck(ctx.guild.id)
        
        # Shuffle the deck
        deck.shuffle()
        
        # Save the updated deck
        await CardDeckManager.save_deck(ctx.guild.id, deck)
        
        # Send confirmation
        embed = discord.Embed(
            title="🔀 Deck Shuffled",
            color=discord.Color.green(),
            description="The deck has been shuffled and all cards have been returned to it."
        )
        embed.add_field(name="Cards in deck", value=f"{deck.remaining_count()} cards", inline=False)
        embed.set_footer(text=f"Shuffled by {ctx.author.name}")
        
        await ctx.send(embed=embed)
        
        # Log the shuffle
        audit_logger.warning(f"User {ctx.author.id} shuffled the deck in guild {ctx.guild.id}")
    
    @commands.command(name="newdeck")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def new_deck(self, ctx: commands.Context):
        """
        Create a fresh shuffled deck for the server.
        
        Usage:
            !newdeck
        """
        if not ctx.guild:
            await ctx.send("❌ This command can only be used in a server.")
            return
        
        # Create a new deck
        deck = CardDeck()
        deck.reset()
        
        # Save the new deck
        await CardDeckManager.save_deck(ctx.guild.id, deck)
        
        # Send confirmation
        embed = discord.Embed(
            title="🆕 New Deck Created",
            color=discord.Color.gold(),
            description="A fresh deck has been created and shuffled."
        )
        embed.add_field(name="Cards in deck", value=f"{deck.remaining_count()} cards", inline=False)
        embed.set_footer(text=f"Created by {ctx.author.name}")
        
        await ctx.send(embed=embed)
        
        # Log the new deck
        audit_logger.warning(f"User {ctx.author.id} created a new deck in guild {ctx.guild.id}")
    
    @commands.command(name="deckinfo")
    async def deck_info(self, ctx: commands.Context):
        """
        Display information about the server's current deck.
        
        Usage:
            !deckinfo
        """
        if not ctx.guild:
            await ctx.send("❌ This command can only be used in a server.")
            return
        
        # Get the server's deck
        deck = await CardDeckManager.get_deck(ctx.guild.id)
        
        # Create embed
        embed = discord.Embed(
            title="🃏 Deck Information",
            color=discord.Color.blue()
        )
        embed.add_field(name="Cards remaining", value=f"{deck.remaining_count()} cards", inline=True)
        embed.add_field(name="Cards drawn", value=f"{len(deck.drawn_cards)} cards", inline=True)
        
        if deck.drawn_cards:
            # Show last 5 drawn cards
            recent_drawn = deck.drawn_cards[-5:]
            embed.add_field(
                name="Recently drawn",
                value=" ".join(recent_drawn),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @draw_card.error
    async def draw_error(self, ctx, error):
        """Handle errors for the draw command."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"❌ Command is on cooldown. Try again in {round(error.retry_after, 1)}s.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument. Please provide a valid number.")
    
    @shuffle_deck.error
    async def shuffle_error(self, ctx, error):
        """Handle errors for the shuffle command."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"❌ Command is on cooldown. Try again in {round(error.retry_after, 1)}s.")
    
    @new_deck.error
    async def new_deck_error(self, ctx, error):
        """Handle errors for the newdeck command."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"❌ Command is on cooldown. Try again in {round(error.retry_after, 1)}s.")


def setup(bot: commands.Bot):
    bot.add_cog(CardDraw(bot))
