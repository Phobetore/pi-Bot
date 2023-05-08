const { SlashCommandBuilder } = require('discord.js');


module.exports = {
    data: new SlashCommandBuilder()
        .setName('ping')
        .setDescription('Repond avec un Pong!'),
    async execute(interaction) {

        await interaction.reply('Pong! `' + (Date.now() - interaction.createdTimestamp) + 'ms`');
    },
};