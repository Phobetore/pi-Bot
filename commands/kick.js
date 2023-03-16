const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('kick')
        .setDescription("Tacler quelqu'un")
        .addUserOption(option =>
            option
            .setName('target')
            .setDescription('qui sera votre victime ?')
            .setRequired(true)),


    async execute(kick) {
        const target = kick.options.getUser('target');




        // EXTRACTION DU JS DE L'API
        const request = require('request');
        let url = "https://api.waifu.pics/sfw/kick";
        let options = { json: true };

        request(url, options, (error, res, body) => {
            if (!error && res.statusCode == 200) {
                // construction de l'Embed à affiché. avec l'url venant de l'api

                if (target == kick.user) {
                    const Reponse = new EmbedBuilder()
                        .setDescription(`You stupid ? Trying hiting your self ?`)
                        .setImage(`https://media.tenor.com/XkjALAfX6p4AAAAC/omori-kel.gif`);
                    kick.reply({ embeds: [Reponse] });
                } else {
                    const Reponse = new EmbedBuilder()
                        .setDescription(`${kick.user} a balayé ${target}`)
                        .setImage(`${body['url']}`);
                    kick.reply({ embeds: [Reponse] });
                }

            };
        });

    }
};