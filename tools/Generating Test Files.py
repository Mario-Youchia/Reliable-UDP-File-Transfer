# Generating Test Files
import random

Random1MB = bytearray(random.getrandbits(8) for _ in range(int(1e6)))
Random10MB = bytearray(random.getrandbits(8) for _ in range(int(10e6)))
Random50MB = bytearray(random.getrandbits(8) for _ in range(int(50e6)))
Random100MB = bytearray(random.getrandbits(8) for _ in range(int(100e6)))

# Write files:
with open("Random1MB", "wb") as f:
    f.write(Random1MB)
with open("Random10MB", "wb") as f:
    f.write(Random10MB)
with open("Random50MB", "wb") as f:
    f.write(Random50MB)
with open("Random100MB", "wb") as f:
    f.write(Random100MB)
