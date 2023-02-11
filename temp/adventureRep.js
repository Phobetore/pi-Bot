const {
    Events,
    EmbedBuilder,
    AttachmentBuilder,
    ActionRowBuilder,
    ButtonBuilder,
    ButtonStyle
} = require('discord.js');

module.exports = {
    name: Events.InteractionCreate,
    async execute(interactionAdventure) {


        if (interactionAdventure.CustomId === 'StorySelect') {

            var storyName = interactionAdventure.values[0].split(",")[0]
            var nameCurrentChoice = interactionAdventure.values[0].split(",")[1]

        } else {

            console.error(interactionAdventure);
            var storyName = interactionAdventure.customId.split(",")[0]
            var nameCurrentChoice = interactionAdventure.customId.split(",")[1]

        }

        var story = require(`../adventureDB/${storyName}/Storyloading`);


        if (nameCurrentChoice != null) {
            // extract the json of the story choosen
            var currentChoice = story.rootChoice;

        } else {

            var currentChoice = story.choices.find(
                choices => choices.name === nameCurrentChoice
            );

        }


        // making a button list
        btnList = [];
        for (let i = 0; i < currentChoice.choices.length; i++) {
            btnList.push(
                new ButtonBuilder()
                .setCustomId(`${storyName},${currentChoice.choices[i]}`)
                .setLabel(currentChoice.choices[i])
                .setStyle(ButtonStyle.Primary)
            );
        }

        const buttons = new ActionRowBuilder().addComponents(btnList);


        // Showing the images
        if (currentChoice.path.length > 1) {
            for (let i = 0; i < currentChoice.path.length; i++) {
                file = new AttachmentBuilder(`adventureDB/${storyName}/${currentChoice.path[i]}`);
                if (i == 0) {
                    afficherRep = new EmbedBuilder()
                        .setColor(0x0099FF)
                        .setTitle(`Histoire : ${story.name}`)
                        .setImage(`attachment://${currentChoice.path[i]}`);

                    await interactionAdventure.update({
                        embeds: [afficherRep],
                        components: [],
                        files: [file]
                    });
                } else {
                    afficherRep = new EmbedBuilder()
                        .setColor(0x0099FF)
                        .setImage(`attachment://${currentChoice.path[i]}`);
                    if (i == currentChoice.path.length - 1) {
                        await interactionAdventure.followUp({
                            embeds: [afficherRep],
                            components: [buttons],
                            files: [file]
                        });
                    } else {
                        await interactionAdventure.followUp({
                            embeds: [afficherRep],
                            components: [],
                            files: [file]
                        });
                    }
                }
            }
        } else {
            file = new AttachmentBuilder(`adventureDB/${storyName}/${currentChoice.path}`);
            afficherRep = new EmbedBuilder()
                .setColor(0x0099FF)
                .setTitle(`Histoire : ${story.name}`)
                .setImage(`attachment://${currentChoice.path}`);

            await interactionAdventure.update({
                embeds: [afficherRep],
                components: [buttons],
                files: [file]
            });
        }

    }
};