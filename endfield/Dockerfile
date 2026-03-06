FROM node:lts-alpine

WORKDIR /app
COPY endfield_test.js ./

# Run as non-root user provided by the official Node image.
USER node

CMD ["node", "endfield_test.js"]
