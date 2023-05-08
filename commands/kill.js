const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('kill')
        .setDescription("Tuer quelqu'un")
        .addUserOption(option =>
            option
            .setName('target')
            .setDescription('qui sera votre victime ?')
            .setRequired(true)),


    async execute(kill) {
        const target = kill.options.getUser('target');




        // EXTRACTION DU JS DE L'API
        const request = require('request');
        let url = "https://api.waifu.pics/sfw/kill";
        let options = { json: true };

        request(url, options, (error, res, body) => {
            if (!error && res.statusCode == 200) {
                // construction de l'Embed à affiché. avec l'url venant de l'api

                if (target == kill.user) {
                    const Reponse = new EmbedBuilder()
                        .setDescription(`You stupid ? Trying to kill your self ?`)
                        .setImage(`https://media.tenor.com/XkjALAfX6p4AAAAC/omori-kel.gif`);
                    kill.reply({ embeds: [Reponse] });
                } else {
                    const Reponse = new EmbedBuilder()
                        .setDescription(`${kill.user} a assassiné ${target}  :skull:`)
                        .setImage(`${body['url']}`);
                    kill.reply({ embeds: [Reponse] });
                }

            };
        });

    }
};