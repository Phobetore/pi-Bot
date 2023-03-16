const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('bite')
        .setDescription("Tacler quelqu'un")
        .addUserOption(option =>
            option
            .setName('target')
            .setDescription('qui sera votre victime ?')
            .setRequired(true)),


    async execute(bite) {
        const target = bite.options.getUser('target');




        // EXTRACTION DU JS DE L'API
        const request = require('request');
        let url = "https://api.waifu.pics/sfw/bite";
        let options = { json: true };

        request(url, options, (error, res, body) => {
            if (!error && res.statusCode == 200) {
                // construction de l'Embed à affiché. avec l'url venant de l'api

                if (target == bite.user) {
                    const Reponse = new EmbedBuilder()
                        .setDescription(`You stupid ? Trying to bite yourself ?`)
                        .setImage(`https://media.tenor.com/XkjALAfX6p4AAAAC/omori-kel.gif`);
                    bite.reply({ embeds: [Reponse] });
                } else {
                    const Reponse = new EmbedBuilder()
                        .setDescription(`${bite.user} a mordu ${target}  :lips:`)
                        .setImage(`${body['url']}`);
                    bite.reply({ embeds: [Reponse] });
                }

            };
        });

    }
};