FROM node:24.19.0-bookworm-slim
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /home/node/app
COPY --chown=node:node frontend/package.json frontend/package-lock.json ./
RUN npm ci && chown -R node:node /home/node/app
COPY --chown=node:node frontend ./
USER node
EXPOSE 3000
CMD ["npm", "run", "dev"]
