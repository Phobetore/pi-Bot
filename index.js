
const Discord =  require("discord.js");
const intents = new Discord.IntentsBitField(8);
const client = new Discord.Client({intents});
const config = require("./config.json");
const fs = require('node:fs');
const path = require('node:path');



// commands loading
client.commands = new Discord.Collection();

const commandsPath = path.join(__dirname, 'commands');
const commandFiles = fs.readdirSync(commandsPath).filter(file => file.endsWith('.js'));

for (const file of commandFiles) {
	const filePath = path.join(commandsPath, file);
	const command = require(filePath);
	// Set a new item in the Collection with the key as the command name and the value as the exported module
	if ('data' in command && 'execute' in command) {
		client.commands.set(command.data.name, command);
	} else {
		console.log(`[WARNING] The command at ${filePath} is missing a required "data" or "execute" property.`);
	}
}




// When the client is ready, run this code (only once)
// We use 'c' for the event parameter to keep it separate from the already defined 'client'
client.once(Discord.Events.ClientReady, c => {
	console.log(`Ready! Logged in as ${c.user.tag}`);
});




// Log in to Discord with your client's token
client.login(config.token);




// setting an activity
client.on('ready', () => {
	
    const activities = [
        "Être ou ne pas être ?",
        "La secte du ban !",
        "3.1415926535",
        "Connaissez-vous Axarathe ?",
        "les oeuvres de Sweet"
    ];

    setInterval(()=>{
    const inter = activities[Math.floor(Math.random()*activities.length)];
    client.user.setActivity(inter, { type: Discord.ActivityType.Watching})},8000
    );

});

