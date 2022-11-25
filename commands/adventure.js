const { ActionRowBuilder, SelectMenuBuilder, EmbedBuilder, SlashCommandBuilder } = require('discord.js');


module.exports = {
	data: new SlashCommandBuilder()
		.setName('adventure')
		.setDescription('test'),

	async execute(interactionAdventure) {


        
        const row = new ActionRowBuilder()
			.addComponents(
				new SelectMenuBuilder()
					.setCustomId('select')
					.setPlaceholder('Selectionner')
					.addOptions(
						{
							label: 'Aventure 1',
							description: 'une description',
							value: 'aventure1',
						},
						{
							label: 'Aventure 2',
							description: 'une description',
							value: 'aventure2',
						},
                        ),
                        );
						
                        
                        const afficher = new EmbedBuilder()
                        .setColor(0x0099FF)
                        .setTitle('AVENTURE INTERACTIVE')
                        .setDescription('Choisissez une aventure:')
                        
                        
                        await interactionAdventure.reply({ embeds: [afficher], components: [row] });
                    },
                };
                
                