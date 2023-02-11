const {
    ActionRowBuilder,
    SelectMenuBuilder,
    EmbedBuilder,
    SlashCommandBuilder
} = require('discord.js');
const fs = require('fs');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('adventure')
        .setDescription('test'),

    async execute(interactionAdventure) {
        const adventureFolders = fs.readdirSync('./adventureDB/');
        storys = [];
        for (let i = 0; i < adventureFolders.length; i++) {
            storys.push({
                label: adventureFolders[i],
                description: 'nom de divinité',
                value: `${adventureFolders[i]},rootChoice`
            });
        }

        const row = new ActionRowBuilder()
            .addComponents(
                new SelectMenuBuilder()
                .setCustomId('StorySelect')
                .setPlaceholder('Selectionner une histoire')
                .addOptions(storys)
            );

        const afficher = new EmbedBuilder()
            .setColor(0x0099FF)
            .setTitle('AVENTURE INTERACTIVE')
            .setDescription('Choisissez une aventure:');
        await interactionAdventure.reply({
            embeds: [afficher],
            components: [row]
        });
    }
};