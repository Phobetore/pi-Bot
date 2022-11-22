const { ActionRowBuilder, SelectMenuBuilder, EmbedBuilder, SlashCommandBuilder } = require('discord.js');


module.exports = {
	data: new SlashCommandBuilder()
		.setName('adventure')
		.setDescription('test'),

	async execute(interaction) {

        if (interaction.customId === 'select') {
            await interaction.update({ content: 'Something was selected!', components: [] });
            console.log('Something was selected!')
        }
    
        const row = new ActionRowBuilder()
			.addComponents(
				new SelectMenuBuilder()
					.setCustomId('select')
					.setPlaceholder('Selectionner')
					.addOptions(
						{
							label: 'premier',
							description: 'une description',
							value: 'first_option',
						},
						{
							label: 'deuxieme',
							description: 'une description',
							value: 'second_option',
						},
					),
			);

        const afficher = new EmbedBuilder()
            .setColor(0x0099FF)
            .setTitle('Titre')
            .setDescription('UNE IMAGE');


        await interaction.reply({ content: 'Peut etre une future commande d\'aventure interactive ?', embeds: [afficher], components: [row] });
	},
};

