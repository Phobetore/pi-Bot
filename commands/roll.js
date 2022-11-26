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


	async execute(interactionRoll) {
		faces = interactionRoll.options.getNumber('faces');
		cible = interactionRoll.options.getString('cible');
		des = interactionRoll.options.getNumber('dés');
        
        if (!cible) {
            cible = interactionRoll.user
        }
        if (!(faces && faces >= 1)) {
            faces = 20
        }

        if ((des && des >= 1)) {
            toReturn = ""
            total = 0
            for (let i = 1; i <= des ; i++) {
                temp = (1 + Math.floor(Math.random() * (faces)));
                toReturn += "\n "+ i +" => " + temp;
                total = total + temp
            }
            await interactionRoll.reply(`**${cible}** rolled: (${des}d${faces}) \nAnd got : ${toReturn} \nTotal: ${total}`);     
        }
        else{
            await interactionRoll.reply(`**${cible}** rolled: (1d${faces}) \n And got : ${1 + Math.floor(Math.random() * (faces))}`);     
        }

        
		
	},
};