import pygame
from pygame.locals import *
import random
from enum import Enum
from typing import Tuple, List
import os

class GameState(Enum):
    MENU = 0
    PLAYING = 1
    GAME_OVER = 2

class Config:
    """Game's configuration constants"""
    SCREEN_WIDTH = 864
    SCREEN_HEIGHT = 936
    FPS = 60
    
    # Physics
    GRAVITY = 0.5
    MAX_FALL_SPEED = 8
    JUMP_STRENGTH = -10
    SCROLL_SPEED = 4
    
    # Game mechanics
    PIPE_GAP = 150
    PIPE_FREQUENCY = 1500  # milliseconds
    GROUND_HEIGHT = 168  # 936 - 768
    
    # Colors
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    YELLOW = (255, 255, 0)
    GREEN = (0, 255, 0)
    
    # Animation
    FLAP_COOLDOWN = 5
    
    # Audio
    MUSIC_VOLUME = 0.7
    SFX_VOLUME = 0.8

class AssetManager:
    """Handles loading and caching of game assets"""
    
    def __init__(self):
        self.images = {}
        self.sounds = {}
        self._load_assets()
    
    def _load_assets(self):
        """Load all game assets"""
        try:
            # Initialize pygame mixer for audio
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            
            # Load images with error handling
            asset_paths = {
                'bg': 'img/bg.png',
                'ground': 'img/ground.png',
                'restart': 'img/restart.png',
                'pipe': 'img/pipe.png'
            }
            
            for name, path in asset_paths.items():
                if os.path.exists(path):
                    self.images[name] = pygame.image.load(path).convert()
                else:
                    # Create placeholder if image doesn't exist
                    self.images[name] = self._create_placeholder(name)
            
            # Load wolf animation frames
            self.images['wolf_frames'] = []
            for i in range(1, 4):
                path = f"img/wolfy{i}.png"
                if os.path.exists(path):
                    self.images['wolf_frames'].append(pygame.image.load(path).convert_alpha())
                else:
                    self.images['wolf_frames'].append(self._create_wolf_placeholder())
            
            # Load audio files
            self._load_audio()
                    
        except pygame.error as e:
            print(f"Error loading assets: {e}")
            self._create_fallback_assets()
    
    def _load_audio(self):
        """Load audio files with error handling"""
        try:
            # Load sound effects
            sound_paths = {
                'swoosh': 'audio/swoosh_point.mp3',
                'point': 'audio/sfx_point.mp3'
            }
            
            for name, path in sound_paths.items():
                if os.path.exists(path):
                    sound = pygame.mixer.Sound(path)
                    sound.set_volume(Config.SFX_VOLUME)
                    self.sounds[name] = sound
                else:
                    # Create placeholder sound (silent)
                    self.sounds[name] = self._create_placeholder_sound()
            
            # Load background music
            music_path = 'audio/bg_music.mp3'
            if os.path.exists(music_path):
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.set_volume(Config.MUSIC_VOLUME)
            else:
                print("Background music not found, game will run without music")
                
        except pygame.error as e:
            print(f"Error loading audio: {e}")
            # Create silent placeholder sounds
            for name in ['swoosh', 'point']:
                self.sounds[name] = self._create_placeholder_sound()
    
    def _create_placeholder_sound(self):
        """Create a silent placeholder sound"""
        # Create a very short silent sound
        sound_array = pygame.sndarray.array([[0, 0]] * 100)
        return pygame.sndarray.make_sound(sound_array)
    
    def _create_placeholder(self, name: str) -> pygame.Surface:
        """Create placeholder surfaces for missing assets"""
        if name == 'bg':
            surf = pygame.Surface((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT))
            surf.fill((135, 206, 235))  # Sky blue
            return surf
        elif name == 'ground':
            surf = pygame.Surface((Config.SCREEN_WIDTH, Config.GROUND_HEIGHT))
            surf.fill((139, 69, 19))  # Brown
            return surf
        elif name == 'pipe':
            surf = pygame.Surface((80, 400))
            surf.fill((0, 128, 0))  # Green
            return surf
        elif name == 'restart':
            surf = pygame.Surface((100, 50))
            surf.fill((255, 0, 0))  # Red
            return surf
        else:
            surf = pygame.Surface((50, 50))
            surf.fill((255, 255, 255))
            return surf
    
    def _create_wolf_placeholder(self) -> pygame.Surface:
        """Create placeholder wolf sprite"""
        surf = pygame.Surface((50, 35))
        surf.fill((255, 255, 0))  # Yellow
        surf.set_colorkey((0, 0, 0))
        return surf
    
    def _create_fallback_assets(self):
        """Create all assets as fallbacks"""
        for name in ['bg', 'ground', 'restart', 'pipe']:
            self.images[name] = self._create_placeholder(name)
        self.images['wolf_frames'] = [self._create_wolf_placeholder() for _ in range(3)]
        
        # Create placeholder sounds
        for name in ['swoosh', 'point']:
            self.sounds[name] = self._create_placeholder_sound()

class Wolf(pygame.sprite.Sprite):
    """Player character class with improved physics and animation"""
    
    def __init__(self, x: int, y: int, asset_manager: AssetManager):
        super().__init__()
        self.asset_manager = asset_manager
        self.images = asset_manager.images['wolf_frames']
        self.image_index = 0
        self.animation_counter = 0
        
        self.image = self.images[self.image_index]
        self.rect = self.image.get_rect(center=(x, y))
        self.mask = pygame.mask.from_surface(self.image)
        
        # Physics
        self.velocity = 0
        self.is_clicked = False
        
        # Store original images for rotation
        self.original_images = self.images.copy()
    
    def update(self, game_state: GameState):
        """Update wolf physics and animation"""
        if game_state == GameState.PLAYING:
            self._apply_physics()
            jump_occurred = self._handle_input()
            self._animate()
            self._rotate_sprite()
            return jump_occurred
        elif game_state == GameState.GAME_OVER:
            self._point_down()
        return False
    
    def _apply_physics(self):
        """Apply gravity and movement"""
        self.velocity += Config.GRAVITY
        self.velocity = min(self.velocity, Config.MAX_FALL_SPEED)
        
        # Only move if not hitting ground
        if self.rect.bottom < Config.SCREEN_HEIGHT - Config.GROUND_HEIGHT:
            self.rect.y += int(self.velocity)
    
    def _handle_input(self):
        """Handle jump input with proper state tracking"""
        mouse_pressed = pygame.mouse.get_pressed()[0]
        
        if mouse_pressed and not self.is_clicked:
            self.is_clicked = True
            self.velocity = Config.JUMP_STRENGTH
            return True  # Jump occurred
        elif not mouse_pressed:
            self.is_clicked = False
        
        return False  # No jump
    
    def _animate(self):
        """Handle sprite animation"""
        self.animation_counter += 1
        
        if self.animation_counter > Config.FLAP_COOLDOWN:
            self.animation_counter = 0
            self.image_index = (self.image_index + 1) % len(self.images)
    
    def _rotate_sprite(self):
        """Rotate sprite based on velocity"""
        angle = max(-90, min(45, self.velocity * -2))
        self.image = pygame.transform.rotate(self.original_images[self.image_index], angle)
        
        # Update rect and mask after rotation
        old_center = self.rect.center
        self.rect = self.image.get_rect()
        self.rect.center = old_center
        self.mask = pygame.mask.from_surface(self.image)
    
    def _point_down(self):
        """Point sprite downward when game over"""
        self.image = pygame.transform.rotate(self.original_images[self.image_index], -90)
        old_center = self.rect.center
        self.rect = self.image.get_rect()
        self.rect.center = old_center
        self.mask = pygame.mask.from_surface(self.image)
    
    def reset(self, x: int, y: int):
        """Reset wolf to initial position"""
        self.rect.center = (x, y)
        self.velocity = 0
        self.is_clicked = False
        self.image_index = 0
        self.animation_counter = 0

class Pipe(pygame.sprite.Sprite):
    """Pipe obstacle class"""
    
    def __init__(self, x: int, y: int, position: int, asset_manager: AssetManager):
        super().__init__()
        self.image = asset_manager.images['pipe'].copy()
        
        if position == 1:  # Top pipe
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect = self.image.get_rect(bottomleft=(x, y - Config.PIPE_GAP // 2))
        else:  # Bottom pipe
            self.rect = self.image.get_rect(topleft=(x, y + Config.PIPE_GAP // 2))
        
        self.mask = pygame.mask.from_surface(self.image)
        self.scored = False
    
    def update(self):
        """Move pipe left and remove when off screen"""
        self.rect.x -= Config.SCROLL_SPEED
        if self.rect.right < 0:
            self.kill()

class Button:
    """UI Button class"""
    
    def __init__(self, x: int, y: int, image: pygame.Surface):
        self.image = image
        self.rect = self.image.get_rect(topleft=(x, y))
        self.is_pressed = False
    
    def update(self) -> bool:
        """Update button state and return if clicked"""
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]
        
        if self.rect.collidepoint(mouse_pos):
            if mouse_pressed and not self.is_pressed:
                self.is_pressed = True
                return True
            elif not mouse_pressed:
                self.is_pressed = False
        
        return False
    
    def draw(self, screen: pygame.Surface):
        """Draw button to screen"""
        screen.blit(self.image, self.rect)

class AudioManager:
    """Manages game audio including music and sound effects"""
    
    def __init__(self, asset_manager: AssetManager):
        self.asset_manager = asset_manager
        self.music_playing = False
        self.music_paused = False
    
    def play_swoosh(self):
        """Play jump/swoosh sound effect"""
        self.asset_manager.sounds['swoosh'].play()
    
    def play_point(self):
        """Play point sound effect"""
        self.asset_manager.sounds['point'].play()
    
    def start_music(self):
        """Start background music"""
        try:
            if not self.music_playing and not self.music_paused:
                pygame.mixer.music.play(-1)  # Loop indefinitely
                self.music_playing = True
            elif self.music_paused:
                pygame.mixer.music.unpause()
                self.music_paused = False
        except pygame.error:
            pass  # Music file might not exist
    
    def stop_music_with_effect(self):
        """Stop music with vinyl record effect"""
        try:
            if self.music_playing:
                # Create a "record stopping" effect by gradually slowing down
                current_pos = pygame.mixer.music.get_pos()
                pygame.mixer.music.stop()
                self.music_playing = False
                self.music_paused = False
        except pygame.error:
            pass
    
    def pause_music(self):
        """Pause the background music"""
        try:
            if self.music_playing:
                pygame.mixer.music.pause()
                self.music_paused = True
        except pygame.error:
            pass

class Game:
    """Main game class handling game logic and state"""
    
    def __init__(self):
        pygame.init()
        
        # Set window icon
        self._set_window_icon()
        
        self.screen = pygame.display.set_mode((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT))
        pygame.display.set_caption('Wolfython - Flappy Bird Style')
        self.clock = pygame.time.Clock()
        
        # Try to load a Flappy Bird style font, fallback to system fonts
        self.font = self._load_game_font()
        
        # Assets management
        self.asset_manager = AssetManager()
        
        # Audio management
        self.audio_manager = AudioManager(self.asset_manager)
        
        # Game's state
        self.state = GameState.MENU
        self.score = 0
        self.ground_scroll = 0
        self.last_pipe_time = 0
        
        # Sprite groups
        self.pipe_group = pygame.sprite.Group()
        self.wolf_group = pygame.sprite.Group()
        
        # Create the character
        self.wolf = Wolf(100, Config.SCREEN_HEIGHT // 2, self.asset_manager)
        self.wolf_group.add(self.wolf)
        
        # Create the UI
        restart_x = Config.SCREEN_WIDTH // 2 - 50
        restart_y = Config.SCREEN_HEIGHT // 2 - 100
        self.restart_button = Button(restart_x, restart_y, self.asset_manager.images['restart'])
        
        # Performance tracking of the game
        self.pipe_passed = False
    
    def _set_window_icon(self):
        """Set the window icon"""
        icon_paths = ['icon.png', 'icon.svg', 'icon.jpg', 'img/icon.png']
        
        for path in icon_paths:
            if os.path.exists(path):
                try:
                    icon = pygame.image.load(path)
                    pygame.display.set_icon(icon)
                    return
                except pygame.error:
                    continue
        
        # Create a simple placeholder icon if no icon file found
        icon = pygame.Surface((32, 32))
        icon.fill(Config.YELLOW)
        pygame.draw.circle(icon, Config.GREEN, (16, 16), 12)
        pygame.display.set_icon(icon)
    
    def _load_game_font(self):
        """Load a Flappy Bird style font"""
        # Try to load custom fonts first
        font_paths = [
            'fonts/flappy.ttf',
        ]
        
        for path in font_paths:
            if os.path.exists(path):
                try:
                    return pygame.font.Font(path, 60)
                except pygame.error:
                    continue
        
        # Fallback to system fonts that look similar
        font_names = ['Impact', 'Arial Black', 'Courier New', 'monospace']
        
        for font_name in font_names:
            try:
                font = pygame.font.SysFont(font_name, 60, bold=True)
                if font:
                    return font
            except:
                continue
        
        # Final fallback
        return pygame.font.Font(None, 60)
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == GameState.MENU:
                    self.state = GameState.PLAYING
                    self.last_pipe_time = pygame.time.get_ticks() - Config.PIPE_FREQUENCY
                    self.audio_manager.start_music()
        
        return True
    
    def update(self):
        """Update game logic"""
        if self.state == GameState.PLAYING:
            self._update_playing()
        elif self.state == GameState.GAME_OVER:
            self._update_game_over()
    
    def _update_playing(self):
        """Update the game during play state"""
        # Update the character's sprites and check for jump
        jump_occurred = self.wolf.update(self.state)
        if jump_occurred:
            self.audio_manager.play_swoosh()
        
        self.pipe_group.update()
        
        # Generate the pipes
        self._generate_pipes()
        
        # Update the ground scroll
        self._update_ground_scroll()
        
        # Check the collisions
        self._check_collisions()
        
        # Update the game's score
        self._update_score()
    
    def _update_game_over(self):
        """Update game during game over state"""
        self.wolf_group.update(self.state)
        
        if self.restart_button.update():
            self._reset_game()
    
    def _generate_pipes(self):
        """Generate pipe pairs at intervals"""
        current_time = pygame.time.get_ticks()
        
        if current_time - self.last_pipe_time > Config.PIPE_FREQUENCY:
            pipe_height = random.randint(-100, 100)
            pipe_center_y = Config.SCREEN_HEIGHT // 2 + pipe_height
            
            # Create the pipe pair
            top_pipe = Pipe(Config.SCREEN_WIDTH, pipe_center_y, 1, self.asset_manager)
            bottom_pipe = Pipe(Config.SCREEN_WIDTH, pipe_center_y, -1, self.asset_manager)
            
            self.pipe_group.add(top_pipe, bottom_pipe)
            self.last_pipe_time = current_time
    
    def _update_ground_scroll(self):
        """Update scrolling ground"""
        self.ground_scroll -= Config.SCROLL_SPEED
        if abs(self.ground_scroll) > 35:
            self.ground_scroll = 0
    
    def _check_collisions(self):
        """Check for the collisions and the boundaries"""
        # Check the pipe collisions using masks for pixel-perfect detection
        for pipe in self.pipe_group:
            if pygame.sprite.collide_mask(self.wolf, pipe):
                self.state = GameState.GAME_OVER
                self.audio_manager.stop_music_with_effect()
                return
        
        # Check the boundaries
        if (self.wolf.rect.top < 0 or 
            self.wolf.rect.bottom >= Config.SCREEN_HEIGHT - Config.GROUND_HEIGHT):
            self.state = GameState.GAME_OVER
            self.audio_manager.stop_music_with_effect()
    
    def _update_score(self):
        """Update and track score"""
        if not self.pipe_group:
            return
        
        wolf_x = self.wolf.rect.centerx
        first_pipe = min(self.pipe_group, key=lambda p: p.rect.centerx)
        
        # Check if the character is between pipes
        if (first_pipe.rect.left < wolf_x < first_pipe.rect.right and not self.pipe_passed):
            self.pipe_passed = True
        
        # Score when the character passes pipe
        if self.pipe_passed and wolf_x > first_pipe.rect.right:
            if not first_pipe.scored:
                self.score += 1
                self.audio_manager.play_point()  # Play point sound
                first_pipe.scored = True
                # Mark the pair as scored
                for pipe in self.pipe_group:
                    if abs(pipe.rect.centerx - first_pipe.rect.centerx) < 10:
                        pipe.scored = True
            self.pipe_passed = False
    
    def _reset_game(self):
        """Reset game to initial state"""
        self.state = GameState.MENU
        self.score = 0
        self.ground_scroll = 0
        self.pipe_passed = False
        
        # Clear pipes
        self.pipe_group.empty()
        
        # Reset wolf
        self.wolf.reset(100, Config.SCREEN_HEIGHT // 2)
        
        # Reset audio
        self.audio_manager.music_playing = False
        self.audio_manager.music_paused = False
    
    def draw(self):
        """Draw all game elements"""
        # Draw background
        self.screen.blit(self.asset_manager.images['bg'], (0, 0))
        
        # Draw pipes and wolf
        self.pipe_group.draw(self.screen)
        self.wolf_group.draw(self.screen)
        
        # Draw ground
        ground_y = Config.SCREEN_HEIGHT - Config.GROUND_HEIGHT
        self.screen.blit(self.asset_manager.images['ground'], (self.ground_scroll, ground_y))
        
        # Draw score with outline effect (like Flappy Bird)
        self._draw_outlined_text(str(self.score), Config.WHITE, Config.BLACK, 
                               Config.SCREEN_WIDTH // 2, 50)
        
        # Draw game over UI
        if self.state == GameState.GAME_OVER:
            self.restart_button.draw(self.screen)
            self._draw_outlined_text("Game Over", Config.WHITE, Config.BLACK,
                                   Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 2 - 200)
        
        # Draw menu instructions
        if self.state == GameState.MENU:
            self._draw_outlined_text("Click to Start", Config.WHITE, Config.BLACK,
                                   Config.SCREEN_WIDTH // 2, Config.SCREEN_HEIGHT // 2 - 200)
    
    def _draw_outlined_text(self, text: str, color: Tuple[int, int, int], 
                          outline_color: Tuple[int, int, int], x: int, y: int):
        """Draw text with outline effect (Flappy Bird style)"""
        # Draw outline
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    outline_surface = self.font.render(text, True, outline_color)
                    outline_rect = outline_surface.get_rect(center=(x + dx, y + dy))
                    self.screen.blit(outline_surface, outline_rect)
        
        # Draw main text
        text_surface = self.font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(x, y))
        self.screen.blit(text_surface, text_rect)
    
    def _draw_text(self, text: str, color: Tuple[int, int, int], x: int, y: int):
        """Draw centered text"""
        text_surface = self.font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(x, y))
        self.screen.blit(text_surface, text_rect)
    
    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            # Handle events
            running = self.handle_events()
            
            # Update
            self.update()
            
            # Draw
            self.draw()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(Config.FPS)
        
        pygame.quit()

def main():
    """Entry point"""
    game = Game()
    game.run()

if __name__ == "__main__":
    main()