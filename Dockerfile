# Dockerfile
# Step 1: Build the React app
FROM node:18 AS build

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json for npm install
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the app
COPY . .

# Expose port 8080
EXPOSE 8080

# Use the 'serve' command to serve the app in production
CMD ["node", "server.js"]