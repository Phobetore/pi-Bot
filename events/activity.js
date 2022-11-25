const { Events, ActivityType } = require('discord.js');

module.exports = {
	name: Events.ClientReady,
	once: true,
	execute(client) {
		const activities = [
            "Être ou ne pas être ?",
            "La secte du ban !",
            "3.1415926535",
            "Connaissez-vous Axarathe ?",
            "les oeuvres de E-Magpie#0682",
            "bot en cours de dev",
            "l'infinité de l'espace"
        ];
    
        setInterval(()=>{
        const inter = activities[Math.floor(Math.random()*activities.length)];
        client.user.setActivity(inter, { type: ActivityType.Watching})},8000
        );
	},
};