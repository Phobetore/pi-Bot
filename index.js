
const Discord =  require("discord.js")
const intents = new Discord.IntentsBitField(8)
const client = new Discord.Client({intents})
const config = require("./config.json")
//const loadCommand = require("./Loader/loadCommand.js")


// When the client is ready, run this code (only once)
// We use 'c' for the event parameter to keep it separate from the already defined 'client'
client.once(Discord.Events.ClientReady, c => {
	console.log(`Ready! Logged in as ${c.user.tag}`);
});

// Log in to Discord with your client's token
client.login(config.token);

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

