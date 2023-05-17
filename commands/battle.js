const { SlashCommandBuilder, ActionRowBuilder, Events, ModalBuilder, TextInputBuilder, TextInputStyle } = require('discord.js');


module.exports = {
    data: new SlashCommandBuilder()
        .setName("battle")
        .setDescription("test modaly"),

    async execute(interaction, client) {
        // Create the modal
        const modal = new ModalBuilder()
            .setCustomId("myModal")
            .setTitle("My Modal");
        // Add components to modal
        // Create the text input components
        const favoriteColorInput = new TextInputBuilder()
            .setCustomId("favoriteColorInput")
            // The label is the prompt the user sees for this input
            .setLabel("What's your favorite color?")
            // Short means only a single line of text
            .setStyle(TextInputStyle.Short);
        const hobbiesInput = new TextInputBuilder()
            .setCustomId("hobbiesInput")
            .setLabel("What's some of your favorite hobbies?")
            // Paragraph means multiple lines of text.
            .setStyle(TextInputStyle.Paragraph);
        // An action row only holds one text input,
        // so you need one action row per text input.
        const firstActionRow = new ActionRowBuilder().addComponents(
            favoriteColorInput
        );
        const secondActionRow = new ActionRowBuilder().addComponents(hobbiesInput);
        // Add inputs to the modal
        modal.addComponents(firstActionRow, secondActionRow);
        // Show the modal to the user
        await interaction.showModal(modal);

        client.on('interactionCreate', async(modalSubmit) => {
            if (!modalSubmit.isModalSubmit()) return;
            // Get the data entered by the user
            const favoriteColor = modalSubmit.fields.getTextInputValue("favoriteColorInput");
            const hobbies = modalSubmit.fields.getTextInputValue("hobbiesInput");
            console.log({ favoriteColor, hobbies });

            const embed = new client.discord.MessageEmbed()
                .setColor("#9900ff")
                .setTitle(favoriteColor)
                .setThumbnail("https://repository-images.githubusercontent.com/568992847/b273970d-11a6-4e69-8c4e-2ae4d3358332")
                .setTimestamp();
            const row = new client.discord.MessageActionRow().addComponents(
                new client.discord.MessageButton()

                .setLabel("ceci est un test")
                .setURL("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
                .setStyle("LINK")
            );

            await modalSubmit.reply({
                embeds: [embed],
                components: [row],
            });
        })
    },
};