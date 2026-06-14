FROM node:22-slim

WORKDIR /app

COPY frontend/package.json ./package.json
RUN npm install

COPY frontend/ ./

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
