const { SlashCommandBuilder } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('say')
        .setDescription("Tacler quelqu'un")
        .addStringOption(option =>
            option
            .setName('message')
            .setDescription('votre message')
            .setRequired(true)),

    async execute(say) {
        const message = say.options.getString('message');

        say.reply(`${message}`);

    }
};