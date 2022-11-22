const { SlashCommandBuilder } = require('discord.js');

module.exports = {
	data: new SlashCommandBuilder()
		.setName('user')
		.setDescription('Provides information about the user.')
		.addUserOption(option =>
			option
				.setName('target')
				.setDescription('vous pouvez le faire pour quelqu\'un')
				.setRequired(false)),


	async execute(interaction) {
		const target = interaction.options.getUser('target');

		if (target) {
			await interaction.reply(`C'est ${target}, tu ne le savais pas ?`);
		}
		else{
			await interaction.reply(`Tu es ${interaction.user}, mais tu le sais déjà, non ?`);
		}
		
	},
};