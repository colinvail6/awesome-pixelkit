import pixelkit as kit
import time
import random

# Fast 3D Perlin-like noise with random seed
class FastNoise:
    def __init__(self, seed=None):
        # Generate random permutation table
        if seed is not None:
            random.seed(seed)
        
        # Create permutation of 0-255 and shuffle manually
        self.perm = list(range(256))
        
        # Fisher-Yates shuffle (since random.shuffle doesn't exist in CircuitPython)
        for i in range(255, 0, -1):
            j = random.randint(0, i)
            self.perm[i], self.perm[j] = self.perm[j], self.perm[i]
        
        # Double the permutation table to avoid overflow
        self.perm = self.perm * 2
        
        # Precalculate fade curve lookup table for speed
        self.fade_table = [self._fade(i / 255.0) for i in range(256)]
    
    def _fade(self, t):
        """Smoothing function for interpolation (only used for precalc)"""
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def fade(self, t):
        """Fast fade using lookup table"""
        return self.fade_table[int(t * 255)]
    
    def lerp(self, t, a, b):
        """Linear interpolation"""
        return a + t * (b - a)
    
    def grad(self, hash_val, x, y, z):
        """Simplified 3D gradient function"""
        h = hash_val & 7  # Reduced from 15 to 7 for speed
        if h < 4:
            return x + y if h & 1 == 0 else -x + y
        else:
            return y + z if h & 1 == 0 else -y + z
    
    def noise(self, x, y, z):
        """Generate 3D Perlin noise value between -1 and 1"""
        # Find unit grid cell containing point
        X = int(x) & 255
        Y = int(y) & 255
        Z = int(z) & 255
        
        # Get relative xyz coordinates within cell
        x -= int(x)
        y -= int(y)
        z -= int(z)
        
        # Compute fade curves using lookup table
        u = self.fade(x)
        v = self.fade(y)
        w = self.fade(z)
        
        # Hash coordinates of the 8 cube corners
        a = self.perm[X] + Y
        aa = self.perm[a] + Z
        ab = self.perm[a + 1] + Z
        b = self.perm[X + 1] + Y
        ba = self.perm[b] + Z
        bb = self.perm[b + 1] + Z
        
        # Blend results from 8 corners of cube
        result = self.lerp(w,
            self.lerp(v,
                self.lerp(u, self.grad(self.perm[aa], x, y, z),
                             self.grad(self.perm[ba], x - 1, y, z)),
                self.lerp(u, self.grad(self.perm[ab], x, y - 1, z),
                             self.grad(self.perm[bb], x - 1, y - 1, z))),
            self.lerp(v,
                self.lerp(u, self.grad(self.perm[aa + 1], x, y, z - 1),
                             self.grad(self.perm[ba + 1], x - 1, y, z - 1)),
                self.lerp(u, self.grad(self.perm[ab + 1], x, y - 1, z - 1),
                             self.grad(self.perm[bb + 1], x - 1, y - 1, z - 1))))
        
        return result


# Initialize noise generator with random seed
noise_gen = FastNoise()

# Animation variables
z_offset = 0.0
z_speed = 0.05  # How fast to move through Z dimension
frame_delay = 0.02  # ~50 FPS (more realistic for ESP32)

def dial_to_scale(dial_value):
    """Convert dial value (0-65535) to scale (0.05 to 2.0)"""
    return 0.05 + (dial_value / 65535.0) * 1.95


def render_perlin_noise():
    """Render 3D Perlin noise to the LED matrix"""
    global z_offset
    
    # Get scale from dial once
    scale = dial_to_scale(kit.dial_value)
    nz = z_offset
    
    # Generate noise for each pixel
    for y in range(8):
        ny = y * scale
        for x in range(16):
            nx = x * scale
            
            # Get noise value (-1 to 1) and convert to 0-1 range
            noise_val = (noise_gen.noise(nx, ny, nz) + 1.0) * 0.5
            
            # Map to rainbow colors using HSV
            hue = int(noise_val * 360)
            kit.set_pixel_hsv(x, y, (hue, 1.0, 0.8))
    
    kit.render()
    z_offset += z_speed


def render_grayscale_noise():
    """Render grayscale 3D Perlin noise (faster)"""
    global z_offset
    
    scale = dial_to_scale(kit.dial_value)
    nz = z_offset
    
    for y in range(8):
        ny = y * scale
        for x in range(16):
            nx = x * scale
            noise_val = (noise_gen.noise(nx, ny, nz) + 1.0) * 0.5
            
            # Convert to grayscale
            brightness = int(noise_val * 255)
            kit.set_pixel(x, y, [brightness, brightness, brightness])
    
    kit.render()
    z_offset += z_speed


def render_fire_noise():
    """Fire effect using 3D Perlin noise"""
    global z_offset
    
    scale = dial_to_scale(kit.dial_value)
    nz = z_offset
    
    for y in range(8):
        ny = y * scale * 0.5
        for x in range(16):
            nx = x * scale
            noise_val = (noise_gen.noise(nx, ny, nz) + 1.0) * 0.5
            
            # Fire colors: dark red -> red -> orange -> yellow -> white
            if noise_val > 0.8:
                color = [255, 255, int((noise_val - 0.8) * 1275)]
            elif noise_val > 0.5:
                color = [255, int((noise_val - 0.5) * 850), 0]
            elif noise_val > 0.2:
                color = [int((noise_val - 0.2) * 850), 0, 0]
            else:
                color = [int(noise_val * 425), 0, 0]
            
            kit.set_pixel(x, y, color)
    
    kit.render()
    z_offset += z_speed * 2


def render_water_noise():
    """Water/ocean effect using 3D Perlin noise"""
    global z_offset
    
    scale = dial_to_scale(kit.dial_value)
    nz = z_offset
    
    for y in range(8):
        ny = y * scale
        for x in range(16):
            nx = x * scale
            noise_val = (noise_gen.noise(nx, ny, nz) + 1.0) * 0.5
            
            # Water colors: dark blue -> cyan -> light blue -> white (foam)
            if noise_val > 0.7:
                brightness = int((noise_val - 0.7) * 850)
                color = [brightness, brightness, 255]
            elif noise_val > 0.4:
                color = [0, int((noise_val - 0.4) * 850), 255]
            else:
                color = [0, 0, int(50 + noise_val * 512)]
            
            kit.set_pixel(x, y, color)
    
    kit.render()
    z_offset += z_speed * 0.7


def render_plasma_noise():
    """Plasma effect combining multiple noise octaves"""
    global z_offset
    
    scale = dial_to_scale(kit.dial_value)
    nz = z_offset
    nz2 = z_offset * 1.5
    
    for y in range(8):
        ny = y * scale
        ny2 = y * scale * 2
        for x in range(16):
            nx = x * scale
            nx2 = x * scale * 2
            
            # Combine multiple octaves for more detail
            val1 = noise_gen.noise(nx, ny, nz)
            val2 = noise_gen.noise(nx2, ny2, nz2) * 0.5
            
            noise_val = (val1 + val2 + 1.0) / 2.5
            
            # Psychedelic plasma colors
            hue = int((noise_val * 360 + z_offset * 50) % 360)
            kit.set_pixel_hsv(x, y, (hue, 1.0, 0.9))
    
    kit.render()
    z_offset += z_speed


# Override button handlers to switch effects
current_effect = 0
effect_names = ["Rainbow", "Grayscale", "Fire", "Water", "Plasma"]

def on_button_a():
    """Switch to next effect"""
    global current_effect
    current_effect = (current_effect + 1) % len(effect_names)
    print(f"Effect: {effect_names[current_effect]}")

def on_button_b():
    """Regenerate noise with new random seed"""
    global noise_gen, z_offset
    noise_gen = FastNoise()  # New random permutation
    z_offset = 0.0
    print("New random noise pattern!")

def on_joystick_up():
    """Speed up Z animation"""
    global z_speed
    z_speed = min(z_speed + 0.01, 0.5)
    print(f"Z speed: {z_speed:.2f}")

def on_joystick_down():
    """Slow down Z animation"""
    global z_speed
    z_speed = max(z_speed - 0.01, 0.01)
    print(f"Z speed: {z_speed:.2f}")

kit.on_button_a = on_button_a
kit.on_button_b = on_button_b
kit.on_joystick_up = on_joystick_up
kit.on_joystick_down = on_joystick_down

# Main loop
print("3D Perlin Noise Demo")
print("Dial: Zoom in/out")
print("Button A: Change effect")
print("Button B: New random pattern")
print("Joystick Up/Down: Adjust speed")

while True:
    kit.check_controls()
    
    # Render current effect
    if current_effect == 0:
        render_perlin_noise()
    elif current_effect == 1:
        render_grayscale_noise()
    elif current_effect == 2:
        render_fire_noise()
    elif current_effect == 3:
        render_water_noise()
    else:
        render_plasma_noise()
    
    # Fixed 60 FPS
    time.sleep(frame_delay)
