FROM node:20-slim

WORKDIR /app
COPY actions-wrapper/package.json actions-wrapper/package-lock.json* ./
RUN npm install --omit=dev

COPY actions-wrapper/server.js ./

ENV PORT=8080
EXPOSE 8080
CMD ["npm", "start"]
