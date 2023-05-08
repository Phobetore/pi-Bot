const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('blush')
        .setDescription("blush"),


    async execute(blush) {

        // EXTRACTION DU JS DE L'API
        const request = require('request');
        let url = "https://api.waifu.pics/sfw/blush";
        let options = { json: true };

        request(url, options, (error, res, body) => {
            if (!error && res.statusCode == 200) {
                const Reponse = new EmbedBuilder()
                    .setDescription(`${blush.user} blush :flushed:`)
                    .setImage(`${body['url']}`);
                blush.reply({ embeds: [Reponse] });
            };
        });

    }
};