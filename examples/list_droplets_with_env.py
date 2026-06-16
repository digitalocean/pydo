
import os
from pydo import Client

# Initialize the client with your DigitalOcean token
# Make sure your environment variable DIGITALOCEAN_TOKEN is set
client = Client(token=os.getenv("DIGITALOCEAN_TOKEN"))

print("Fetching list of your DigitalOcean droplets...\n")

# List all available droplets in your account
droplets = client.droplets.list()
for d in droplets["droplets"]:
    print(f"ID: {d['id']}, Name: {d['name']}, Status: {d['status']}")
