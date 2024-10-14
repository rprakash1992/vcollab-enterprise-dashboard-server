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

# Build the React app
RUN npm run build

# Step 2: Serve the app with serve -s build
FROM node:18 AS production

# Install 'serve' globally
RUN npm install -g serve

# Set the working directory in the new container
WORKDIR /app

# Copy the built app from the previous stage
COPY --from=build /app/build ./build

# Expose port 8080
EXPOSE 8080

# Use the 'serve' command to serve the app in production
CMD ["serve", "-s", "build", "-l", "8080"]