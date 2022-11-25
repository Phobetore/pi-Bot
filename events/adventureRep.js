const { Events, EmbedBuilder, AttachmentBuilder } = require('discord.js');

module.exports = {
	name: Events.InteractionCreate,
	async execute(interactionAdventure) {
    
        if (!interactionAdventure.isSelectMenu()) return;

        if (interactionAdventure.customId === 'select') {

            if (interactionAdventure.values == "aventure1") {
                file = new AttachmentBuilder('./img/lain.gif');

                afficherRep = new EmbedBuilder()
                .setColor(0x0099FF)
                .setTitle('l\'aventure numero 1')
                .setImage('attachment://lain.gif');
                
            }
            else{
                file = new AttachmentBuilder('./img/lain2.gif');

                afficherRep = new EmbedBuilder()
                .setColor(0x0099FF)
                .setTitle('l\'aventure numero 2')
                .setImage('attachment://lain2.gif');
            }

            await interactionAdventure.update({ embeds: [afficherRep], components: [], files: [file] });
        }
	},
};