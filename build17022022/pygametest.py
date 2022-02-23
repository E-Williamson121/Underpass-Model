import pygame, os, time, random, math, heatmaps
import perlinnoise as perlin

# ==============================================================================================================================#
# Main utility functions

# utility function for generating a sigmoid curve
def sigmoid(x):
    return(1/(1+math.exp(-x)))

# utility function for generating a windmap, given a seeding value from -1 to 1.
def set_windmap(value=0):
    # wind varies from left to right on a -1 to 1 scale
    windmap = [[0.45-0.1*value, 0.45, 0.45+0.1*value],
               [0.45-0.2*value, 0.7, 0.45+0.2*value],
               [0.45-0.1*value, 0.45, 0.45+0.1*value]]
    return(windmap)

# ==============================================================================================================================#
# Neighbour class

class Neighbours():
    """Struct for holding tile neighbourhood (using this exclusively for lookups ensures we don't look at any tiles we shouldn't)."""
    def __init__(self, x, y, width, height, tiles):
        self.width = width
        self.height = height

        # store references to each possible neighbour
        self.L = self.refer(x-1, y, tiles)
        self.R = self.refer(x+1, y, tiles)
        self.U = self.refer(x, y-1, tiles)
        self.D = self.refer(x, y+1, tiles)
        self.UL = self.refer(x-1, y-1, tiles)
        self.UR = self.refer(x+1, y-1, tiles)
        self.DL = self.refer(x-1, y+1, tiles)
        self.DR = self.refer(x+1, y+1, tiles)

    def refer(self, tx, ty, tiles):
        """References a neighbour if one exists, stores None otherwise."""
        if tx > -1 and tx < self.width:
            if ty > -1 and ty < self.height:
                return(tiles[ty][tx])

    def lookup(self, direction):
        """Returns a neighbour if one exists, returns None otherwise."""
        return(getattr(self, direction, None))


# ==============================================================================================================================#
# Tile class

class Tile():
    """Tile class: currently just a skeleton for a coloured square, but will have more importance later when tiles have infection rules."""

    # ==============================================================================================================================#
    # initialization
    
    def __init__(self, x, y, typ, app):
        """Initialization function, makes tile of a given type at a given position, by default tiles are uninhabited and exits are closed."""
        self.x   = x
        self.y   = y
        self.typ = typ
        self.prevtyp = self.typ
        self.updated = False
        
        self.preferences = None
        self.id = None

        self.screen = app.screen
        self.colours = app.colours
        self.colourmap = app.colourmap
        
        self.tiles = app.tileset
        self.tol = app.tol
        self.width = app.width
        self.height = app.height

        self.weights = [2, 0.5, 0.5, 0.5] # (will adjust to add more specificity to repulsion based on person type soon!)
        self.initialheat = [heatmaps.Base.boarding.map[y][x],
                            heatmaps.Base.departing.map[y][x],
                            heatmaps.Base.left.map[y][x],
                            heatmaps.Base.right.map[y][x]]

        self.State = [0, {}]
        self.PrevState = [0, {}]
        
        if self.typ != 0:
            self.rect = pygame.Rect((self.x)*app.scale,
                                    (self.y)*app.scale,
                                    app.scale, app.scale)
            pygame.draw.rect(self.screen, self.colourtile(self.typ), self.rect)#, 1)

    # ==============================================================================================================================#
    # spread ruleset

    def SpreadTiles(self, i, windmap=None):
        """Algorithm for distributing spread to neighbour tiles."""
        x, y = self.x, self.y
        if i == 0:
            # applies only if the current cell has a non-zero value (values below tolerance are effectively zero)
            if self.PrevState[i] > self.tol:
                # a useful constant for readability.
                Pv = self.PrevState[i]

                # set the Pvs of the surrounding cells based on the windmap.
                self.setv("UL", Pv*windmap[0][0], i)
                self.setv("L", Pv*windmap[1][0], i)
                self.setv("DL", Pv*windmap[2][0], i)

                self.setv("U", Pv*windmap[0][1], i)
                self.setv("D", Pv*windmap[2][1], i)

                self.setv("UR", Pv*windmap[0][2], i)
                self.setv("R", Pv*windmap[1][2], i)
                self.setv("DR", Pv*windmap[2][2], i)
        else:
            for key in self.PrevState[i]:
                if self.PrevState[i][key] > 0:
                    # a useful constant for readability.
                    Pv = self.PrevState[i][key]

                    # set the Pvs of the surrounding cells, distancing is propagated purely in cardinal directions.
                    self.setv("L", Pv-1, i, key)
                    self.setv("R", Pv-1, i, key)
                    self.setv("U", Pv-1, i, key)
                    self.setv("D", Pv-1, i, key)

    def setv(self, d, nv, i, key=None):
        """Sets the Pv of the target cell at (tx, ty) to nv if the current value is < nv."""
        target = self.neighbours.lookup(d)
        if target:
            if i == 0:
                if target.State[i] <= nv:
                    target.State[i] = nv
            else:
                if key in target.State[i]:
                    if target.State[i][key] <= nv:
                        target.State[i][key] = nv
                else:
                    target.State[i][key] = nv

    # ==============================================================================================================================#
    # person updating ruleset

    def PersonRules(self, fullmove=True):
        """Outer function controlling person movement, includes the despawn conditions."""
        ai = self.typ - 4

        # generate spread
        self.State[0] = 1
        self.State[1][self.id] = 8
        
        # despawn rules
        if fullmove:
            if (ai == 1 and self.prevtyp == 4) or (ai == 2 and self.prevtyp == 3):
                if self.prevtyp == 4:
                    self.typ = self.prevtyp
                    self.id, self.preferences = None, None
                    self.updated = True
                    return()
            
            elif (ai == 3 and self.x == 219) or (ai == 4 and self.x == 0):
                    self.typ, self.prevtyp = 3, 3
                    self.id, self.preferences = None, None
                    self.updated = True
                    return()
                
        # movement
        self.move_person(ai, fullmove)


    def move_person(self, ai, fullmove=True):
        """Functionality handling how people move. First, tiles are tested in decreasing preference order."""
        """subsequently, motion is made in the optimal direction."""
        if not self.updated:
            bestd = ""
            mini = self.getheat(ai, self.id)

            for pd in self.preferences:
                t = self.test_tile(pd, self.tiles, self.id, ai)
                if t < mini or (t == mini and bestd == ""):
                    mini = t
                    bestd = pd

            if bestd != "":
                target = self.neighbours.lookup(bestd)

                target.State[0] = 1
                target.State[1][self.id] = 8  

                if fullmove:
                    target.prevtyp = target.typ
                    target.typ = self.typ
                    self.typ = self.prevtyp
                    
                    target.id = self.id
                    self.id = None
                    
                    target.preferences = self.preferences
                    self.preferences = None
                    
                    target.updated, self.updated = True, True             
                
            else:
                self.State[1][self.id] = 8
                self.State[0] = 1

    def test_tile(self, d, tilemap, idx, ai):
        """Functionality for obtaining the heatmap value of a tile in the given direction of motion."""
        target = self.neighbours.lookup(d)
        if target: return(target.getheat(ai, idx))
        else: return(10000000)

    def getheat(self, ai, idx):
        """function for obtaining heat value for the current tile."""
        myid = None
        distancing_value = 0
        
        if idx in self.PrevState[1]: myid = self.PrevState[1].pop(idx)
        if len(self.PrevState[1]) > 0: distancing_value = (self.weights[ai-1])*max(self.PrevState[1].values())

        if myid: self.PrevState[1][idx] = myid

        return(self.initialheat[ai-1] + distancing_value)

    # ==============================================================================================================================#
    # person spawn ruleset
    
    def SpawningRules(self, tick):
        """Function for spawning people."""
        # entrance tile spawning rules
        if self.typ == 3:
            
            if self.x < 5 and self.y == 30:                     # left entrance
                target = self.neighbours.lookup("R")
                if target.typ == 1:
                    prefs = ["R", "UR", "DR", "D", "U", "DL", "UL", "L"]
                    
                    if random.randint(0, 100) < 10:             # 10% chance of spawning boarder
                        self.spawn_person(target, tick, 5, prefs)
                    elif random.randint(0, 100) < 0:            # 2% chance of spawning right walker
                        self.spawn_person(target, tick, 7, prefs)

            elif self.x > 215 and self.y == 30:                 # right entrance
                target = self.neighbours.lookup("L")
                if target.typ == 1:
                    prefs = ["L", "UL", "DL", "D", "U", "DR", "UR", "R"]
                    
                    if random.randint(0, 100) < 10:             # 10% chance of spawning boarder
                        self.spawn_person(target, tick, 5, prefs)
                    elif random.randint(0, 100) < 0:            # 2% chance of spawning left walker
                        self.spawn_person(target, tick, 8, prefs)
                        
            elif self.y < 0 and self.x == 25 or self.x == 195:  # upper entrances
                target = self.neighbours.lookup("D")
                if target.typ == 1:
                    if random.randint(0, 100) < 5:              # 5% chance of spawning boarder
                        if self.x > 110: prefs = ["D", "DL", "L", "UL", "U", "DR", "UR", "R"]
                        else: prefs = ["D", "DR", "R", "UR", "U", "DL", "UL", "L"]
                        
                        self.spawn_person(target, tick, 5, prefs)

    def spawn_person(self, target, tick, typ, prefs):
        target.typ, target.id, target.preferences, target.updated = typ, f'f{tick}x{self.x}y{self.y}t{typ}', prefs, True

    # ==============================================================================================================================#
    # overall update ruleset

    def UpdateRules(self, tick, windmap):
        """Function controlling the update rules."""
        if self.typ != 0:
            self.SpreadTiles(0, windmap)                # Pv spread
            self.SpreadTiles(1)                         # Distancing spread

            if tick == round(tick):
                # motion frames
                if (self.typ == 3 or self.typ == 4) and round(tick) % 4 == 0:
                    self.SpawningRules(tick)            # on every 4th motion frame, attempt spawning

                if self.typ in [5,6,7,8]:
                    self.PersonRules()                  # move people and force spread
            else:
                if self.typ in [5,6,7,8]:
                    self.PersonRules(False)             # force spread and propagate an estimate of where people will move

    # ==============================================================================================================================#
    # visuals and post-processing update

    def UpdateVisuals(self, tick, windmap):
        """Routine for updating tiles. Controls the periodic arrival of buses, as well as spread of pathogens."""
        if self.typ != 0:
            # propagate cell decay
            self.PrevState = self.State

            self.State = [0, {}]
            self.State[0] = self.PrevState[0]*windmap[1][1]

            for key in self.PrevState[1]:
                if self.PrevState[1][key] > 1:
                    self.State[1][key] = self.PrevState[1][key] - 1

        # manage opening/closing of bus stop exit tiles
        if self.prevtyp == 2:
            if tick % 600 == 500:
                self.typ = 4
                self.prevtyp = 4
                self.id = None
                self.preferences = None
                self.updated = True
                pygame.draw.rect(self.screen, self.colourtile(self.typ), self.rect, 1)
        elif self.prevtyp == 4:
            if tick % 600 == 1:
                self.typ = 2
                self.prevtyp = 2
                self.id = None
                self.preferences = None
                self.updated = True
                pygame.draw.rect(self.screen, self.colourtile(self.typ), self.rect)#, 1)

        # update appearance if told to
        if self.updated:
            pygame.draw.rect(self.screen, self.colourtile(self.typ), self.rect)#, 1)
            self.updated = False

        # or if state values suggest we should
        if self.typ != 0:
            if not self.PrevState[1] == {}:
                pygame.draw.rect(self.screen, self.colourtile(self.typ), self.rect)#, 1)
                
    def colourtile(self, typ):
        """function for getting tile colour based on tile type."""
        if typ == 1:
            return(self.shadeinred(self.colourmap[self.x]))
        elif self.typ in [0, 2, 5, 6, 7, 8]:
            return(self.colours[typ])
        else:
            return(self.shadeinred(self.colours[typ]))

    def shadeinred(self, col):
        """function for shading tiles, will be based on Pv, but currently displays distancing metric."""
        if self.State[1] == {}: Pv = 0
        elif max(self.State[1].values()) > 8: Pv = 1
        else: Pv = max(self.State[1].values())/8
        (r, g, b, a) = col
        n = int((255-r)*(1 - (1 - Pv)**2))
        return((r+n,g,b,a))

# ==============================================================================================================================#
# Window class

class Window():

    # ==============================================================================================================================#
    # initialization
    
    def __init__(self, height, width, scale):
        """Window initialization."""
        # attribute variables
        self.height = height
        self.width = width
        self.scale = scale
        self.tick = 0

        # note that, as perlin noise sets random.seed = floor(self.perlincount + 1) every frame,
        # all simulation randomness is actually entirely determined by the initial value below.
        self.perlincount = 1256471#random.randint(0, 10000000) # seed randomly
        print(f"initial seed: {self.perlincount}")  # test seeds: [4502191, 1256471]
        self.perlin = perlin.perlin1d

        # wind
        self.wind = set_windmap(self.perlin(self.perlincount/15))
        self.perlincount += 1

        # spread tolerance value
        self.tol = 0.05

        # pygame window properties
        pygame.init()
        self.screen = pygame.display.set_mode((self.width*self.scale, self.height*self.scale))
        self.screen.fill("black")
        self.clock = pygame.time.Clock()

        # main grid setup
        self.grid = []
        self.tileset = []
        
        # tile type colours
        self.colours = ["invisible",                                        # wall - not rendered to save on processing
                        "spec",                                             # air - coloured specially based on the gradient generated below
                        pygame.Color("red"),                                # closed exit - coloured red
                        pygame.Color("gold"),                               # entrance - coloured gold
                        pygame.Color("green"),                              # open exit - coloured green
                        pygame.Color("blue"),                               # boarder - coloured blue
                        pygame.Color("light green"),                        # departer - coloured light green
                        pygame.Color("orange"), pygame.Color("orange")]     # walkers (both directions) - coloured orange

        # gradient bg colour
        self.colourmap = []

        for i in range(0, 110):
            n = int(150 - 100/110 * i)
            self.colourmap.append((n,n,n,0))
        self.colourmap = self.colourmap + (self.colourmap[::-1])

        self.initialize_grid()
        self.generate_display()

        # begin mainloop
        self.mainloop()

    def initialize_grid(self):
        """Function for creating underlying tile map for the grid. Currently the sizes and locations of corridors are hard-coded."""
        # setup underlying grid
        for y in range(0, self.height):
            row = []
            for x in range(0, self.width):
                if y < 21:
                    row.append(0 if (x < 10 or (x > 35 and x < 184) or x > 209) else (1 if y != 0 else 3))
                else:
                    if x == 0 or x == 219: row.append(3)
                    else: row.append(1 if ((x < 100) or (x > 119) or y != 39) else 2)
            self.grid.append(row)

    def generate_display(self):
        """Function for generating tile grid during initialization."""
        # generate cells
        for y in range(0, self.height):
            row = []
            for x in range(0, self.width):
                row.append(Tile(x, y, self.grid[y][x], self))
            self.tileset.append(row)

        # define cell neighbourhoods
        for y in range(0, self.height):
            for x in range(0, self.width):
                tile = self.tileset[y][x]
                tile.neighbours = Neighbours(x, y, self.width, self.height, self.tileset)

    # ==============================================================================================================================#
    # main functionality

    def mainloop(self):
        """Main loop functionality for the program. People are updated first, then tile updates are propagated."""

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    os._exit(0)
            
            # update wind
            perlinvalue = self.perlin(self.perlincount/15)
            self.wind = set_windmap((2*sigmoid(1.5*(perlinvalue)) - 1)/(sigmoid(1)-sigmoid(-1)))
            self.perlincount += 1

            # increment tick count
            self.tick += 1/8

            # CA update
            self.update_tileset()

            pygame.display.update()

            self.clock.tick(30)     # debug: 60 fps
            #self.clock.tick(240)    # cap fps (8 updates every 1/30th second, so 8*30 = 240

    def update_tileset(self):
        """Update loop for all tiles on each tick."""
        # applies update rules to all tiles, then applies update visuals to all tiles
        tick = round(self.tick, 1)
        list(map(lambda x: list(map(lambda t: t.UpdateRules(tick, self.wind), x)), self.tileset))
        list(map(lambda x: list(map(lambda t: t.UpdateVisuals(tick, self.wind), x)), self.tileset))


# ==============================================================================================================================#
# test code

Window(40, 220, 5)
