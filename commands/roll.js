const { SlashCommandBuilder } = require('discord.js');

module.exports = {
	data: new SlashCommandBuilder()
		.setName('roll')
		.setDescription('Permet de lancer un dés')
        .addNumberOption(option =>
            option
                .setName('dés')
                .setDescription('Vous pouvez choisir le nombre de dés')
                .setRequired(false))
		.addNumberOption(option =>
			option
				.setName('faces')
				.setDescription('Vous pouvez choisir le nombre de faces')
				.setRequired(false))
        .addStringOption(option =>
            option
                .setName('cible')
                .setDescription('Vous pouvez definir un personnage à cibler')
                .setRequired(false)),


	async execute(interaction) {
		faces = interaction.options.getNumber('faces');
		cible = interaction.options.getString('cible');
		des = interaction.options.getNumber('dés');
        
        if (!cible) {
            cible = interaction.user
        }
        if (!(faces && faces >= 1)) {
            faces = 20
        }

        if ((des && des >= 1)) {
            toReturn = ""
            for (let i = 1; i <= des ; i++) {
                toReturn += "\n "+ i +" => " + (1 + Math.floor(Math.random() * (faces)));
            }
            await interaction.reply(`**${cible}** rolled: (${des}d${faces}) \nAnd got : ${toReturn}`);     
        }
        else{
            await interaction.reply(`**${cible}** rolled: (1d${faces}) \n And got : ${1 + Math.floor(Math.random() * (faces))}`);     
        }

        
		
	},
};