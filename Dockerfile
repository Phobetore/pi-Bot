FROM node:18-alpine
WORKDIR /pi-bot
COPY . .
RUN yarn install --production
RUN node deploy-commands.js
CMD ["node", "index.js"]