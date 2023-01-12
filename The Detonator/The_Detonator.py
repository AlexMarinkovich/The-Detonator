"""
IDEAS:
* two players controlled at once (easy to code in, just put two players in the map)
* entity teleporter
* tiles that can be destroyed by bombs
* magnet entities

TO DO:
* make levels!
* rework images
* make vortex image lower resolution
* fix entity above head movement
"""

import pygame
import sys
from os import listdir
from math import atan2, sqrt, cos, sin
from collections import defaultdict

# setup
sys.stdout = sys.stderr # allows printing to output before script finishes
pygame.init()
scaled_window = pygame.display.set_mode((800,450), pygame.RESIZABLE)
window = pygame.Surface((1920,1080))
SF = 1
pygame.display.set_caption("The Detonator")
clock = pygame.time.Clock()
FPS = 60
button_font = pygame.font.Font(f'data/font/{listdir("data/font")[0]}', 90)
title_font = pygame.font.Font(f'data/font/{listdir("data/font")[0]}', 180)

# music
background_music = pygame.mixer.Sound('data/sounds/background_music.mp3')
background_music.set_volume(0.2)
background_music.play(loops = -1) # loops infinitely

# read images from files
def read_image(file_location, opacity):
    if opacity == "opaque":
        return pygame.image.load(file_location).convert()
    elif opacity == "transparent":
        return pygame.image.load(file_location).convert_alpha()

images = {}
for folder in listdir('data/graphics'):
    try:
        with open(f'data/graphics/{folder}/reading.txt','r') as f:
            for i in f.readlines():
                file_name, opacity = i.split()

                if file_name[-4:] == ".png": 
                    images[file_name[:-4]] = [read_image(f'data/graphics/{folder}/{file_name}', opacity)]
                else:
                    images[file_name] = [read_image(f'data/graphics/{folder}/{file_name}/{fr}', opacity) for fr in listdir(f'data/graphics/{folder}/{file_name}')]
    except FileNotFoundError: pass

# read sounds from files
sounds = {}
for file in listdir('data/sounds'):
    sounds[file[:-4]] = pygame.mixer.Sound(f'data/sounds/{file}')

# read levels from files
level_maps = defaultdict(list)
level_legends = defaultdict(dict)
level_list = []
for file in listdir('data/levels'):
    with open(f'data/levels/{file}') as f:
        level_name = file[:-4]
        level_list.append(level_name)

        while line := f.readline().strip():
            level_maps[level_name].append(list(line))

        while line := f.readline().strip():
            key, val = line.split("=")
            level_legends[level_name][key.strip()] = val.strip()

# animations class
class Animation:
    def __init__(self, images, *, frame_duration=None, **kwargs):
        self.animation_index = 0
        self.image = images[0]
        self.images = images
        self.frame_duration = frame_duration
        self.counter = 0
    
    def update(self):
        if self.frame_duration is None: return
        if self.counter == self.frame_duration:
            self.counter = 0
            self.animation_index += 1
            if self.animation_index == len(self.images): self.animation_index = 0
            self.image = self.images[self.animation_index]

        self.counter += 1

# level classes
class Object(pygame.sprite.Sprite, Animation):
    def __init__(self, pos, dimensions, images, *, centered=False, **kwargs):
        pygame.sprite.Sprite.__init__(self)
        Animation.__init__(self, images, **kwargs)
        self.rect = pygame.Rect(pos, dimensions)

        if centered: self.rect.center = pos
    
    def update(self):
        Animation.update(self)

class Vortex(Object):
    def __init__(self, pos, dimensions, images, **kwargs):
        super().__init__(pos, dimensions, images, **kwargs)

    def check_win(self):
        if pygame.sprite.collide_rect(self, tile_map.player.sprite):
            tile_map.player.sprite.in_vortex = True

    def update(self):
        super().update()
        self.check_win()

class Entity(Object):
    def __init__(self, pos, dimensions, images, **kwargs):
        super().__init__(pos, dimensions, images, **kwargs)
        self.dx = 0
        self.dy = 0
        self.standing = False
        self.premoved = False

    def gravity(self):
        if not self.standing:
            self.dy += tile_map.tile_size / 62.5

    def movement(self):
        old_x, old_y = self.rect.x, self.rect.y

        # check x direction collisions with tiles
        self.rect.x += round(self.dx)
        self.borders()
        for tile in (hit_list := pygame.sprite.spritecollide(self, tile_map.tiles, False)):
            if self.dx > 0:
                self.rect.right = tile.rect.left
            else:
                self.rect.left = tile.rect.right
        
        if hit_list: self.dx = self.rect.x - old_x

        # check x direction collisions with other entities
        remove_list = []
        for entity in pygame.sprite.spritecollide(self, tile_map.entities, False):
            if entity is self: continue
            tile_map.entities.remove(self)
            remove_list.append(self)
            
            # do movement of entity on the reciever end first
            entity.dx = self.dx
            entity.premoved = True
            entity.movement()

            # check if still colliding after movement applied
            if pygame.sprite.collide_rect(self, entity):
                if self.dx > 0:
                    self.rect.right = entity.rect.left
                else:
                    self.rect.left = entity.rect.right
                self.dx = self.rect.x - old_x

        for entity in remove_list: tile_map.entities.add(entity)

        # check y direction collisions
        self.standing = False
        self.rect.y += round(self.dy)
        for tile in (hit_list := pygame.sprite.spritecollide(self, tile_map.tiles, False)):
            if self.dy > 0:
                self.rect.bottom = tile.rect.top
                self.standing = True
            else:
                self.rect.top = tile.rect.bottom
        
        if hit_list: self.dy = self.rect.y - old_y

        # check y direction collisions with other entities
        remove_list = []
        for entity in pygame.sprite.spritecollide(self, tile_map.entities, False):
            if entity is self: continue
            tile_map.entities.remove(self)
            remove_list.append(self)
            
            # do movement of entity on the reciever end first
            entity.dy = self.dy
            entity.premoved = True
            entity.movement()

            # check if still colliding after movement applied
            if pygame.sprite.collide_rect(self, entity):
                if self.dy > 0:
                    self.rect.bottom = entity.rect.top
                    self.standing = True
                else:
                    self.rect.top = entity.rect.bottom
                self.dy = self.rect.y - old_y
        
        for entity in remove_list: tile_map.entities.add(entity)

        # friction (gotta work to make this real friction later)
        if self.standing: self.dx = 0

    def borders(self):
        if self.rect.left < 0:
            self.rect.left = 0
            self.dx = 0
        elif self.rect.right > tile_map.total_width:
            self.rect.right = tile_map.total_width
            self.dx = 0

        if self.rect.y > tile_map.total_height + 2500:
            self.kill()

    def update(self):
        self.gravity()
        if not self.premoved: self.movement()
        self.premoved = False
        super().update()

class Bomb(Entity):
    def __init__(self, pos, dimensions, images, **kwargs):
        super().__init__(pos, dimensions, images, **kwargs)
        self.image = images[-1]
        self.ignited = False
        self.timer = 180 # 60 fps means this is 3 seconds
        
    def ignition(self):
        if pygame.mouse.get_pressed()[0] and self.rect.collidepoint(mouse_x + camera.view_rect.x, mouse_y + camera.view_rect.y):
            self.ignited = True
            self.frame_duration = 60
            self.animation_index = 0
            self.image = self.images[self.animation_index]

    def countdown(self):
        if self.ignited:
            if self.timer == 0:
                self.explode()
                return

            if self.timer % 60 == 0: sounds["bomb_blip"].play()

            self.timer -= 1
            
    def explode(self):
        sounds["bomb_explode"].play()
        self.kill()
        for entity in tile_map.entities:
            dist = sqrt((self.rect.centerx - entity.rect.centerx)**2 + (self.rect.centery - entity.rect.centery)**2) / tile_map.tile_size
            angle = atan2(entity.rect.centery - self.rect.centery, entity.rect.centerx - self.rect.centerx)
            if dist > 4 or dist == 0: continue

            blast_force_x = 0.51*tile_map.tile_size*cos(angle) / dist
            blast_force_y = 0.51*tile_map.tile_size*sin(angle) / dist
            
            if (entity.dx < 0 and blast_force_x < 0) or (entity.dx > 0 and blast_force_x > 0): entity.dx += blast_force_x
            else: entity.dx = blast_force_x

            if (entity.dy < 0 and blast_force_y < 0) or (entity.dy > 0 and blast_force_y > 0): entity.dy += blast_force_y
            else: entity.dy = blast_force_y

        tile_map.visuals.add(Explosion(self))

    def update(self):
        if not self.ignited: self.ignition()
        self.countdown()
        if self.timer > 0: super().update()

class Explosion(Object):
    def __init__(self, bomb):
        super().__init__(bomb.rect.center, (bomb.rect.width*2, bomb.rect.height*2), tile_map.resized_images["explosion"], centered=True, frame_duration=5)
        self.timer = len(tile_map.resized_images["explosion"]) * 5

    def countdown(self):
        self.timer -= 1
        if self.timer == 0: self.kill()

    def update(self):
        super().update()
        self.countdown()

class Player(Entity):
    def __init__(self, pos, dimensions, images, **kwargs):
        super().__init__(pos, dimensions, images, **kwargs)
        self.WALKING_SPEED = dimensions[0] / 10
        self.input_dx = 0
        self.in_vortex = False
        self.opacity = 255
        self.load_new_level = None

    def player_input(self):
        keys = pygame.key.get_pressed()
        if self.standing and keys[pygame.K_SPACE]: self.dy = tile_map.tile_size / -4
        if self.standing: self.input_dx = 0

        if not(keys[pygame.K_a] != keys[pygame.K_d]): # both or none of left/right keys are pressed
            if abs(self.dx) <= self.WALKING_SPEED and self.input_dx != 0: 
                self.dx = 0
            self.input_dx = 0
            return
        
        if keys[pygame.K_a]: self.input_dx = -self.WALKING_SPEED
        elif keys[pygame.K_d]: self.input_dx = self.WALKING_SPEED
        
        if abs(self.dx) <= self.WALKING_SPEED:
            self.dx = self.input_dx

    def void(self):
        if self.rect.y > tile_map.total_height + 2000:
            self.load_new_level = tile_map.level_name

    def fade(self):
        if self.opacity == 255: sounds["player_teleport"].play()
        
        self.opacity -= 10
        for i in self.images:
            i.set_alpha(self.opacity)

        if self.opacity <= -300: 
            next_level_idx = level_list.index(tile_map.level_name) + 1
            if next_level_idx == len(level_list): mode.set_mode("level_selection")
            else: self.load_new_level = level_list[next_level_idx]

    def update(self):
        self.player_input() 
        super().update()
        self.void()
        if self.in_vortex: self.fade()
        else: camera.update(self)

class Camera:
    def __init__(self, pos: tuple, dimensions: tuple, focus: tuple):
        self.view_rect = pygame.Rect(pos, dimensions)
        self.focus_rect = pygame.Rect(0, 0, dimensions[0]*focus[0], dimensions[1]*focus[1])
        self.focus_rect.center = (dimensions[0] / 2, dimensions[1] / 2)
        self.rect_displacement = (self.focus_rect.x - self.view_rect.x, self.focus_rect.y - self.view_rect.y)

    def update(self, player):
        # x direction
        if player.rect.left > self.focus_rect.right:
            self.focus_rect.right = player.rect.left
            self.view_rect.x = self.focus_rect.x - self.rect_displacement[0]
        
        elif player.rect.right < self.focus_rect.left:
            self.focus_rect.left = player.rect.right
            self.view_rect.x = self.focus_rect.x - self.rect_displacement[0]

        # x direction borders
        if self.view_rect.left < 0: 
            self.view_rect.left = 0
            self.focus_rect.x = self.view_rect.x + self.rect_displacement[0] 

        elif self.view_rect.right > tile_map.total_width: 
            self.view_rect.right = tile_map.total_width
            self.focus_rect.x = self.view_rect.x + self.rect_displacement[0]

        # y direction
        if player.rect.top > self.focus_rect.bottom:
            self.focus_rect.bottom = player.rect.top
            self.view_rect.y = self.focus_rect.y - self.rect_displacement[1]
        
        elif player.rect.bottom < self.focus_rect.top:
            self.focus_rect.top = player.rect.bottom
            self.view_rect.y = self.focus_rect.y - self.rect_displacement[1]
        
        # y direction borders
        if self.view_rect.top < 0: 
            self.view_rect.top = 0
            self.focus_rect.y = self.view_rect.y + self.rect_displacement[1] 

        elif self.view_rect.bottom > tile_map.total_height: 
            self.view_rect.bottom = tile_map.total_height
            self.focus_rect.y = self.view_rect.y + self.rect_displacement[1]

class TileMap:
    def __init__(self, level_name):
        self.level_name = level_name
        self.paused = False

        self.matrix = level_maps[level_name]
        #self.tile_size = min(window.get_width() // len(self.matrix[0]),  window.get_height() // len(self.matrix))
        self.tile_size = 60
        self.total_width = len(self.matrix[0]) * self.tile_size
        self.total_height = len(self.matrix) * self.tile_size
        self.screen = pygame.Surface((self.total_width, self.total_height))

        self.legend = level_legends[level_name]
        self.resized_images = {img_name: [pygame.transform.scale(i,(self.tile_size,self.tile_size)) for i in images[img_name]] for img_name in self.legend.values() if img_name != "air"}
        self.resized_images["explosion"] = [pygame.transform.scale(i,(self.tile_size*2,self.tile_size*2)) for i in images["explosion"]]
        self.resized_images["vortex"] = [pygame.transform.scale(i,(self.tile_size*1.4,self.tile_size*1.4)) for i in images["vortex"]]

        self.tiles = pygame.sprite.Group()
        self.interactables = pygame.sprite.Group()
        self.entities = pygame.sprite.Group()
        self.visuals = pygame.sprite.Group()
        self.player = pygame.sprite.GroupSingle()

        self.image_allignments = {} # used for objects with: topleft point rect != topleft point image

        for y,row in enumerate(self.matrix):
            for x,val in enumerate(row):
                tile_name = self.legend[val]
                if tile_name == "player":
                    object = Player((x * self.tile_size, y * self.tile_size), (self.tile_size, self.tile_size), self.resized_images[tile_name])
                    self.entities.add(object)
                    self.player.add(object)

                elif tile_name == "vortex":
                    object = Vortex((x * self.tile_size, y * self.tile_size), (self.tile_size, self.tile_size), self.resized_images[tile_name], frame_duration = 5)
                    self.interactables.add(object)
                    self.image_allignments[object] = (-0.2*self.tile_size, -0.2*self.tile_size)

                elif tile_name == "bomb":
                    object = Bomb((x * self.tile_size, y * self.tile_size), (self.tile_size, self.tile_size), self.resized_images[tile_name])
                    self.entities.add(object)

                elif tile_name == "crate" or tile_name == "bomb":
                    object = Entity((x * self.tile_size, y * self.tile_size), (self.tile_size, self.tile_size), self.resized_images[tile_name])
                    self.entities.add(object)

                elif tile_name != "air":
                    if tile_name[:4] == "left":
                        object = Object((x*self.tile_size + 0.1*self.tile_size, y * self.tile_size), (0.9*self.tile_size, self.tile_size), self.resized_images[tile_name])
                        self.tiles.add(object)
                        self.image_allignments[object] = (-0.1*self.tile_size, 0)

                    elif tile_name[:5] == "right":
                        object = Object((x * self.tile_size, y * self.tile_size), (0.9*self.tile_size, self.tile_size), self.resized_images[tile_name])
                        self.tiles.add(object)

                    else:
                        object = Object((x * self.tile_size, y * self.tile_size), (self.tile_size, self.tile_size), self.resized_images[tile_name])
                        self.tiles.add(object)            

# GUI classes
class Text:
    def __init__(self, pos: tuple, text: str, font: pygame.font.Font, color, centered=True, antialias=True):
        self.text = text
        text_lines = text.split('\n')
        self.surface_list = [font.render(line, antialias, color) for line in text_lines]
        self.rect_list = [surface.get_rect(center=pos) if centered else surface.get_rect(topleft=pos) for surface in self.surface_list]
        y_incr = self.rect_list[0].height
        for i,rect in enumerate(self.rect_list): rect.y += i * y_incr

    def draw(self, surface):
        for surf, rect in zip(self.surface_list, self.rect_list): surface.blit(surf, rect)

class Button:
    def __init__(self, pos: tuple, dimensions: tuple, text, default_color="white", highlight_color="grey", text_color="black", font=button_font, centered=True):
        self.rect = pygame.Rect(pos, dimensions)
        if centered: self.rect.center = pos

        self.default_color = default_color
        self.highlight_color = highlight_color
        self.color = default_color

        self.text = Text(pos, text, font, text_color)
    
    def pressed(self) -> bool:
        if self.rect.collidepoint(mouse_x, mouse_y):
            self.color = self.highlight_color
            if mouse_clicked: 
                sounds["button_select"].play()
                return True
        else:
            self.color = self.default_color

        return False

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect) # fill
        pygame.draw.rect(surface, "black", self.rect, 2) # outline
        self.text.draw(surface)

# mode setup
class Mode:
    def __init__(self, new_mode):
        self.set_mode(new_mode)
    
    def __repr__(self) -> str:
        return self._value

    def __eq__(self, other) -> bool:
        return self._value == other

    def set_mode(self, new_mode, level="1-1"):
        self._value = new_mode

        if new_mode == "menu":
            global menu_background, menu_text, play_button, help_button, exit_button
            menu_background = pygame.transform.scale(images["background2"][0], window.get_size())

            menu_text = Text((window.get_width()//2, 180), "The Detonator", title_font, "red")
            play_button = Button((960,400), (800,150), "Play")
            help_button = Button((960,650), (800,150), "How To Play")
            exit_button = Button((960,900), (800,150), "Quit Game")

        elif new_mode == "play":
            global tile_map, camera, level_text, play_background, sun, pause_surface, paused_text, resume_button, restart_button, levels_button, menu_button
            tile_map = TileMap(level)
            camera = Camera((0,0), window.get_size(), (0.2, 0.3))
            camera.update(tile_map.player.sprite)

            level_text = Text((20,20), level, button_font, "black", centered=False)
            play_background = pygame.transform.scale(images["background1"][0], tile_map.screen.get_size())
            sun = pygame.Surface((100,100)).convert()
            pygame.Surface.fill(sun,"gold")
            
            # for pause screen
            pause_surface = pygame.Surface(window.get_size())
            pause_surface.set_alpha(100)

            paused_text = Text((window.get_width()//2, 180), "Paused", title_font, "white")
            resume_button = Button((960,400), (800,150), "Resume")
            restart_button = Button((730,650), (340,150), "Restart")
            levels_button = Button((1190,650), (340,150), "Levels")
            menu_button = Button((960,900), (800,150), "Menu")

        elif new_mode == "level_selection":
            global level_selection_buttons, level_selection_text, page_number
            page_number = 0

            level_selection_text = Text((window.get_width()//2, 180), "Levels", title_font, "black")
            level_selection_buttons = [Button((450 + 250*(i%5) + 1920*(i//10), 400 + 250*(i//5%2)),(150,150), level_name) for i,level_name in enumerate(level_list)]
            menu_button = Button((960,900), (800,150), "Menu")

        elif new_mode == "how_to_play":
            global how_to_play_title, how_to_play_text
            how_to_play_title = Text((window.get_width()//2, 180), "How To Play", title_font, "black")

            with open(f'data/how_to_play.txt','r') as f: how_to_play = f.read()
            how_to_play_text = Text((window.get_width()//2, 300), how_to_play, button_font, "black")
            menu_button = Button((960,900), (800,150), "Menu")

mode = Mode("menu")

def unscaled_pos(pos):
    return int(pos[0] * window.get_width() / scaled_window.get_width()), int(pos[1] * window.get_height() / scaled_window.get_height())

while True:
    mouse_x, mouse_y = unscaled_pos(pygame.mouse.get_pos())
    mouse_clicked = False
    keys = set() # stores keys pressed on the current frame
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_clicked = True
            # print(f"Mouse: {mouse_x, mouse_y}")
        
        elif event.type == pygame.KEYDOWN:
            keys.add(event.unicode.lower())

        elif event.type == pygame.WINDOWRESIZED:
            SF = min(scaled_window.get_width() / window.get_width(), scaled_window.get_height() / window.get_height())
    
    if mode == "play":
        # functionality of objects
        if not tile_map.paused:
            tile_map.entities.update()
            tile_map.interactables.update()
            tile_map.tiles.update()
            tile_map.visuals.update()
        
        for object, (allignment_x, allignment_y) in tile_map.image_allignments.items(): 
            object.rect.x += allignment_x
            object.rect.y += allignment_y

        # drawing of objects
        tile_map.screen.blit(play_background, (0,0))
        tile_map.screen.blit(sun, (0,0))
        
        tile_map.tiles.draw(tile_map.screen)
        tile_map.visuals.draw(tile_map.screen)
        tile_map.interactables.draw(tile_map.screen)
        tile_map.entities.draw(tile_map.screen)

        for object, (allignment_x, allignment_y) in tile_map.image_allignments.items(): 
            object.rect.x -= allignment_x
            object.rect.y -= allignment_y
        
        # shows hitboxes of all objects
        # for group in (tile_map.tiles, tile_map.visuals, tile_map.interactables, tile_map.entities):
        #     for object in group:
        #             pygame.draw.rect(tile_map.screen, "red", object.rect, 1)

        # shows hitbox of camera.focus_rect
        # pygame.draw.rect(tile_map.screen, "red", camera.focus_rect, 1)

        window.blit(tile_map.screen,(-camera.view_rect.x, -camera.view_rect.y))
        level_text.draw(window)

        if tile_map.player.sprite.load_new_level: mode.set_mode("play", level = tile_map.player.sprite.load_new_level)

        if tile_map.paused:
            window.blit(pause_surface, (0,0))
            paused_text.draw(window)

            if resume_button.pressed(): tile_map.paused = not tile_map.paused
            resume_button.draw(window)
            
            if restart_button.pressed(): mode.set_mode("play", tile_map.level_name)
            restart_button.draw(window)

            if levels_button.pressed(): mode.set_mode("level_selection")
            levels_button.draw(window)

            if menu_button.pressed(): mode.set_mode("menu")
            menu_button.draw(window)
        
        if 'r' in keys: sounds["button_select"].play(); mode.set_mode("play", tile_map.level_name)
        if '\x1b' in keys: tile_map.paused = not tile_map.paused

    elif mode == "menu":
        window.blit(menu_background, (0,0))
        menu_text.draw(window)

        if play_button.pressed(): mode.set_mode("level_selection")
        play_button.draw(window)

        if help_button.pressed(): mode.set_mode("how_to_play")
        help_button.draw(window)

        if exit_button.pressed(): pygame.quit(); sys.exit()
        exit_button.draw(window)

    elif mode == "level_selection":
        window.blit(menu_background, (0,0))
        level_selection_text.draw(window)

        for level_button in level_selection_buttons:
            if level_button.pressed(): mode.set_mode("play", level = level_button.text.text)
            level_button.draw(window)
        
        if menu_button.pressed(): mode.set_mode("menu")
        menu_button.draw(window)

    elif mode == "how_to_play":
        window.blit(menu_background, (0,0))
        how_to_play_title.draw(window)
        how_to_play_text.draw(window)

        if menu_button.pressed(): mode.set_mode("menu")
        menu_button.draw(window)
        
    scaled_window.blit(pygame.transform.smoothscale(window, scaled_window.get_size()), (0,0)) # height width ratio is variable
    # scaled_window.blit(pygame.transform.smoothscale(window, (window.get_width()*SF, window.get_height()*SF)), (0,0)) # height width ratio is constant

    pygame.display.update()
    clock.tick(FPS) # while True loop wont run faster than 60 times per second