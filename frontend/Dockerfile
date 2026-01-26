FROM node:20

WORKDIR /app

# Install pnpm globally
RUN npm install -g pnpm

# Copy only package files first (cache dependencies)
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install

# Copy the rest of the code
COPY . .

# Start the app
CMD ["pnpm", "start"]
