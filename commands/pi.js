const { SlashCommandBuilder } = require('discord.js');


module.exports = {
	data: new SlashCommandBuilder()
		.setName('pi')
		.setDescription('Les decimale de pi !'),
	async execute(interaction) {
		
		await interaction.reply( Math.PI.toString() );
	},
};