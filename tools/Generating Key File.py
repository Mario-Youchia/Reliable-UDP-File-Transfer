import string
import random

# File length
length = 100000

# Possible characters
characters = string.ascii_letters + string.digits + string.punctuation

# Generate the random string
key = ''.join(random.choice(characters) for i in range(length))

# Write the random string to a file
with open('Key File.txt', 'w') as file:
    file.write(key)
