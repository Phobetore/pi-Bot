const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('bully')
        .setDescription("Bully quelqu'un")
        .addUserOption(option =>
            option
            .setName('target')
            .setDescription('qui sera votre victime ?')
            .setRequired(true)),


    async execute(bully) {
        const target = bully.options.getUser('target');




        // EXTRACTION DU JS DE L'API
        const request = require('request');
        let url = "https://api.waifu.pics/sfw/bully";
        let options = { json: true };

        request(url, options, (error, res, body) => {
            if (!error && res.statusCode == 200) {
                // construction de l'Embed à affiché. avec l'url venant de l'api

                if (target == bully.user) {
                    const Reponse = new EmbedBuilder()
                        .setDescription(`You stupid ? Trying to bully yourself ?`)
                        .setImage(`https://media.tenor.com/XkjALAfX6p4AAAAC/omori-kel.gif`);
                    bully.reply({ embeds: [Reponse] });
                } else {
                    const Reponse = new EmbedBuilder()
                        .setDescription(`${bully.user} a bully ${target}`)
                        .setImage(`${body['url']}`);
                    bully.reply({ embeds: [Reponse] });
                }

            };
        });

    }
};