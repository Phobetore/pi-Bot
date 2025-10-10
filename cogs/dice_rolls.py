import re
import random
import numpy as np
import discord
from discord.ext import commands
from typing import Optional, List, Tuple
import logging
import asyncio

from main import CACHE, audit_logger, get_server_language, TRANSLATIONS


# ─────────────────────────────────────────────
#    Gestion du cache via une classe utilitaire
# ─────────────────────────────────────────────
class CacheManager:
    """
    Classe utilitaire pour la gestion du cache des préférences utilisateurs et des statistiques.
    Utilise un asyncio.Lock pour garantir la sécurité des accès en écriture.
    """
    _lock = asyncio.Lock()

    @staticmethod
    def get_colors() -> dict:
        """Retourne le dictionnaire des couleurs disponibles."""
        return CACHE.get("user_preferences", {}).get("colors", {})

    @staticmethod
    def get_user_color_name(user_id: int) -> str:
        """
        Récupère le nom de la couleur préférée de l'utilisateur depuis le cache.
        Retourne 'bleu' par défaut.
        """
        return CACHE.get("user_preferences", {}) \
                    .get("users", {}) \
                    .get(str(user_id), {}) \
                    .get("color", "bleu")

    @staticmethod
    async def set_user_color(user_id: int, color: str):
        """
        Met à jour la couleur préférée de l'utilisateur dans le cache de manière sécurisée.
        
        Exemple:
            await CacheManager.set_user_color(123456, "rouge")
        """
        async with CacheManager._lock:
            if "user_preferences" not in CACHE:
                CACHE["user_preferences"] = {}
            if "users" not in CACHE["user_preferences"]:
                CACHE["user_preferences"]["users"] = {}
            if str(user_id) not in CACHE["user_preferences"]["users"]:
                CACHE["user_preferences"]["users"][str(user_id)] = {}
            CACHE["user_preferences"]["users"][str(user_id)]["color"] = color

    @staticmethod
    async def increment_user_dice_stats(user_id: int):
        """
        Incrémente le compteur de jets de dés pour l'utilisateur dans le cache.
        
        Exemple:
            await CacheManager.increment_user_dice_stats(123456)
        """
        async with CacheManager._lock:
            if "user_stats" not in CACHE:
                CACHE["user_stats"] = {}
            if str(user_id) not in CACHE["user_stats"]:
                CACHE["user_stats"][str(user_id)] = {"dice_rolls_count": 0}
            CACHE["user_stats"][str(user_id)]["dice_rolls_count"] += 1


# ─────────────────────────────────────────────
#    Parser d'expressions de dés
# ─────────────────────────────────────────────
class DiceExpressionParser:
    """
    Classe utilitaire pour analyser les expressions de dés.

    Exemple:
        expression = "2d6+3-2"
        dice_list, modifier_tokens, numeric_modifiers = DiceExpressionParser.parse(expression)
        # dice_list = [(2, 6, 1)]
        # modifier_tokens = ["+3", "-2"]
        # numeric_modifiers = 1
    """
    @staticmethod
    def parse(expression: str) -> Tuple[List[Tuple[int, int, int]], List[str], int]:
        pattern = r"([+-]?\d+[dD]\d+)|([+-]\d+)"
        matches = re.findall(pattern, expression)

        dice_list = []
        modifier_tokens = []
        numeric_modifiers = 0

        for match in matches:
            dice_part = match[0]
            numeric_part = match[1]

            if dice_part:
                sign = 1 if not dice_part.startswith('-') else -1
                unsigned_dice = dice_part.lstrip('+-')
                try:
                    rolls_str, faces_str = unsigned_dice.split('d')
                    rolls = int(rolls_str)
                    faces = int(faces_str)
                except Exception as e:
                    raise ValueError(f"Invalid dice format in '{dice_part}'.") from e

                # Validation des paramètres pour la sécurité et éviter les abus.
                if rolls > 50 or faces > 99999 or rolls <= 0 or faces <= 0:
                    prefix = '+' if sign == 1 else '-'
                    raise ValueError(f"Invalid expression: {prefix}{rolls}d{faces}. Limit exceeded or negative.")
                dice_list.append((rolls, faces, sign))

            elif numeric_part:
                modifier_tokens.append(numeric_part)
                try:
                    numeric_modifiers += int(numeric_part)
                except Exception as e:
                    raise ValueError(f"Invalid numeric modifier '{numeric_part}'.") from e

        return dice_list, modifier_tokens, numeric_modifiers


# ─────────────────────────────────────────────
#    Cog du bot pour la gestion des jets de dés
# ─────────────────────────────────────────────
class DiceRolls(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_user_color(self, user_id: int) -> discord.Color:
        """
        Retourne un discord.Color à partir du nom de couleur stocké dans le cache.
        """
        color_name = CacheManager.get_user_color_name(user_id)
        hex_color = CacheManager.get_colors().get(color_name, "0x3498db")
        try:
            return discord.Color(int(hex_color, 16))
        except Exception:
            # Retourne une couleur par défaut en cas d'erreur de conversion.
            return discord.Color(0x3498db)

    def roll_dice(self, dice_list: List[Tuple[int, int, int]]) -> Tuple[int, str, str]:
        """
        Exécute les lancers de dés en fonction de la liste fournie.

        Pour de petits nombres de dés (moins de 5), utilise random.randint pour optimiser.
        Sinon, numpy.random.randint est utilisé pour des performances accrues.
        Retourne le total, un résumé des lancers et les résultats détaillés.
        """
        total = 0
        rolls_summary = []
        detailed_results = []

        for (rolls, sides, sign) in dice_list:
            if rolls < 5:
                results = [random.randint(1, sides) for _ in range(rolls)]
                local_total = sign * sum(results)
            else:
                results = np.random.randint(1, sides + 1, size=rolls)
                local_total = sign * int(results.sum())
                results = results.tolist()  # Conversion pour affichage

            total += local_total
            rolls_summary.append(f"{rolls}d{sides}: {', '.join(map(str, results))}")
            for result in results:
                detailed_results.append(f"{sign * result}")

        return total, "\n".join(rolls_summary), " + ".join(detailed_results)

    def build_embed(
        self,
        ctx: commands.Context,
        total: int,
        rolls_summary: str,
        detailed_results: str,
        modifier_expr: Optional[str] = None,
        target_name: Optional[str] = None,
    ) -> discord.Embed:
        """
        Construit et retourne un embed Discord pour présenter le résultat du jet de dés.
        Le champ "Calculation" est ajouté uniquement s'il y a plusieurs valeurs de dés ou un modificateur.
        """
        lang = get_server_language(ctx.guild.id)
        tr = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
        color = self.get_user_color(ctx.author.id)

        embed_title = f"🎲 {tr['embed_result']}: **{total}**"
        embed_description = f"🔻 {tr['embed_for']} **{target_name}**" if target_name else None

        embed = discord.Embed(
            title=embed_title,
            description=embed_description,
            color=color
        )

        if rolls_summary:
            embed.add_field(
                name=tr["embed_dice_details"],
                value=rolls_summary,
                inline=False
            )

        # Affiche le champ "Calculation" seulement s'il y a plus d'un résultat ou un modificateur.
        if modifier_expr or (detailed_results and len(detailed_results.split(" + ")) > 1):
            parts = []
            if detailed_results:
                parts.append(detailed_results)
            if modifier_expr:
                parts.append(modifier_expr)
            calc_field = " + ".join(parts)
            calc_field = calc_field.replace(" + -", " - ")
            embed.add_field(
                name=tr["embed_calculation"],
                value=calc_field,
                inline=False
            )

        # Récupérer l'avatar spécifique au serveur si disponible
        if hasattr(ctx.author, "guild_avatar") and ctx.author.guild_avatar:
            avatar_url = ctx.author.guild_avatar.url
        else:
            avatar_url = ctx.author.avatar.url if ctx.author.avatar else None

        embed.set_footer(
            text=f"{tr['embed_rolled_by']} {ctx.author.display_name}",
            icon_url=avatar_url
        )
        return embed

    @commands.command(name="roll", aliases=["r"])
    @commands.cooldown(1, 3, commands.BucketType.user)  # 1 commande / 3s par utilisateur
    @commands.max_concurrency(1, per=commands.BucketType.user, wait=False)
    async def roll(self, ctx: commands.Context, *, args: str = None):
        """
        Lance des dés avec un format comme '2d6+3'.
        Optionnellement, ajoutez un nom de cible.

        Exemples:
            !roll 2d6+3 Goblin
            !r CibleUnique  (utilise le jet par défaut si défini)
        """
        try:
            from main import get_server_default_roll
            default_roll = get_server_default_roll(ctx.guild.id)

            if not args:
                if default_roll is None:
                    await ctx.send(f"❌ Aucun jet par défaut défini. Veuillez fournir un argument ou configurer {ctx.prefix}defaultroll.")
                    return
                else:
                    args = default_roll

            if len(args) > 100:
                return await ctx.send("❌ Input too long. Limit: 100 characters.")

            # Séparation de l'expression de dés et du nom de cible éventuel.
            parts = args.split(" ", 1)
            dice_list, modifier_tokens, modifiers_total = DiceExpressionParser.parse(parts[0])
            target_name = parts[1] if len(parts) > 1 else None

            # Cas particulier si aucun dé ou modificateur n'est détecté.
            if not dice_list and not modifier_tokens and len(parts) == 1:
                if default_roll is None:
                    return await ctx.send("❌ Invalid format. Exemple: 2d6+3 Goblin.")
                else:
                    dice_list, modifier_tokens, modifiers_total = DiceExpressionParser.parse(default_roll)
                    if not dice_list and not modifier_tokens:
                        return await ctx.send(f"❌ Le default_roll n'est pas valide. Veuillez configurer {ctx.prefix}defaultroll.")
                    target_name = parts[0]

            if not dice_list and not modifier_tokens:
                return await ctx.send("❌ Invalid format. Example: 2d6+3 Goblin.")

            # Exécution des lancers de dés.
            dice_total, rolls_summary, detailed_results = self.roll_dice(dice_list)
            total = dice_total + modifiers_total

            # Préparation de l'expression des modificateurs (suppression du signe "+" initial pour les nombres positifs).
            formatted_modifiers = []
            for token in modifier_tokens:
                if token.startswith('+'):
                    formatted_modifiers.append(token[1:])
                else:
                    formatted_modifiers.append(token)
            modifier_expr = " + ".join(formatted_modifiers)
            modifier_expr = modifier_expr.replace(" + -", " - ")

            # Mise à jour des statistiques dans le cache.
            await CacheManager.increment_user_dice_stats(ctx.author.id)

            # Audit si le total dépasse une certaine limite.
            if total > 999:
                audit_logger.warning(f"High dice roll by {ctx.author}: {total}")

            embed = self.build_embed(
                ctx,
                total=total,
                rolls_summary=rolls_summary,
                detailed_results=detailed_results,
                modifier_expr=modifier_expr,
                target_name=target_name
            )
            # Envoi du message avec un ping discret dans le contenu, suivi de l'embed.
            await ctx.send(
                content=f"",
                # content=f"<@{ctx.author.id}>",
                embed=embed,
                allowed_mentions=discord.AllowedMentions(users=True)
            )

        except ValueError as e:
            await ctx.send(f"❌ {e}")
        except commands.CommandError as ce:
            await ctx.send(f"❌ Command error: {ce}")
        except Exception as e:
            await ctx.send("❌ An error occurred.")
            audit_logger.error(f"Unhandled error in roll command: {e}")

    @roll.error
    async def roll_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument. Check the documentation with {ctx.prefix}help.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"❌ Command is on cooldown. Try again in {round(error.retry_after, 1)}s.")

    @commands.command(name="setcolor")
    async def set_color(self, ctx, color: str):
        """
        Définit la couleur préférée de l'utilisateur.
        Vérifie que la couleur est parmi les options disponibles dans le cache.
        """
        colors = CacheManager.get_colors()
        if color not in colors:
            await ctx.send(f"❌ Couleur non reconnue. Options : {', '.join(colors.keys())}")
            return
        await CacheManager.set_user_color(ctx.author.id, color)
        await ctx.send(f"✅ Votre couleur préférée est maintenant : {color}.")

    @commands.command(name="getcolor")
    async def get_color(self, ctx):
        """
        Affiche la couleur préférée de l'utilisateur.
        """
        color_name = CacheManager.get_user_color_name(ctx.author.id)
        await ctx.send(f"🎨 Votre couleur préférée est : {color_name}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(DiceRolls(bot))
