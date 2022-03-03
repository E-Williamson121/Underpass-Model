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
    windmap = [[0.45-0.2*value, 0.45, 0.45+0.2*value],
               [0.45-0.3*value, 0.7, 0.45+0.3*value],
               [0.45-0.2*value, 0.45, 0.45+0.2*value]]
    return(windmap)

# ==============================================================================================================================#
# Neighbour class

class Neighbours():
    """Struct for holding tile neighbourhood (using this exclusively for lookups ensures we don't look at any tiles we shouldn't)."""
    def __init__(self, x, y, width, height, tiles):
        self.width = width
        self.height = height

        # store references to each possible neighbour
        self.dirs = {}
        self.dirs["L"] = self.refer(x-1, y, tiles)
        self.dirs["R"] = self.refer(x+1, y, tiles)
        self.dirs["U"] = self.refer(x, y-1, tiles)
        self.dirs["D"] = self.refer(x, y+1, tiles)
        self.dirs["UL"] = self.refer(x-1, y-1, tiles)
        self.dirs["UR"] = self.refer(x+1, y-1, tiles)
        self.dirs["DL"] = self.refer(x-1, y+1, tiles)
        self.dirs["DR"] = self.refer(x+1, y+1, tiles)

    def refer(self, tx, ty, tiles):
        """References a neighbour if one exists, stores None otherwise."""
        if tx > -1 and tx < self.width:
            if ty > -1 and ty < self.height:
                return(tiles[ty][tx])

    def lookup(self, direction):
        """Returns a neighbour if one exists, returns None otherwise."""
        return(self.dirs[direction])

# reciprocal neighbour relations (Direction from us to neighbour : Direction from neighbour to us)
reciprocals = {"R":"L", "L":"R", "U":"D", "D":"U", "UL":"DR", "UR":"DL", "DL":"UR", "DR":"UL"}
directions = {"R": (1, 2), "L":(1, 0), "U":(0, 1), "D":(2, 1), "UL":(0, 0), "UR":(0, 2), "DL":(2, 0), "DR":(2, 2)}
TICKSIZE = 9

def direction_preferences(ai):
    if ai == 1: return ["L", "R", "U", "D", "UL", "UR", "DL", "DR"]
    elif ai == 2: return ["L", "D", "DL", "DR", "R", "UL", "UR", "U"]
    elif ai == 3: return ["R", "U", "UR", "UL", "L", "DR", "DL", "D"]
    elif ai == 4: return ["R", "UR", "DR", "U", "D", "UL", "DL", "L"]
    else: return ["L", "DL", "UL", "D", "U", "DR", "UR", "R"]

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

        self.screen = app.screen
        self.colours = app.colours
        self.colourmap = app.colourmap
        self.tol = app.tol

        self.weights = [(2,0), (0,2), (0,2), (0,2), (0,2)] # (will adjust to add more specificity to repulsion based on person type soon!)
        self.initialheat = [heatmaps.Base.boarding.map[y][x],
                            heatmaps.Base.departing.map[y][x],
                            heatmaps.Base.departing.map[y][x],
                            heatmaps.Base.left.map[y][x],
                            heatmaps.Base.right.map[y][x]]

        self.historylength = 3
        self.State = {"Pv":0,
                      "CanSpawn": True,
                      "PersonDir": None,
                      "PersonType": None,
                      "Infection": False,
                      "Carrier": False,
                      "BoarderWaveType":0,
                      "BoarderWaveHistory":[0 for i in range(self.historylength)],
                      "DeparterWaveType":0,
                      "DeparterWaveHistory":[0 for i in range(self.historylength)]}
        
        self.PrevState = {"Pv":0,
                          "CanSpawn": True,
                          "PersonDir": None,
                          "PersonType": None,
                          "Infection": False,
                          "Carrier": False,
                          "BoarderWaveType":0,
                          "BoarderWaveHistory":[0 for i in range(self.historylength)],
                          "DeparterWaveType":0,
                          "DeparterWaveHistory":[0 for i in range(self.historylength)]}
        
        if self.typ != 0:
            self.rect = pygame.Rect((self.x)*app.scale,
                                    (self.y)*app.scale,
                                    app.scale, app.scale)
            pygame.draw.rect(self.screen, self.colourtile(self.typ), self.rect)#, 1)

    # ==============================================================================================================================#
    # spread ruleset

    def SpreadTiles(self, windmap=None):
        """Algorithm for distributing spread to neighbour tiles."""
        if self.typ in [5,6,7,8,9] and self.State["Carrier"]:
            self.State["Pv"] = 30
        else:
            # set Pv to be largest of previous neighbour values
            for d in ["UL", "L", "DL", "U", "D", "UR", "R", "DR"]:
                target = self.neighbours.lookup(reciprocals[d])
                if target:
                    if target.PrevState["Pv"] != 0:
                        y, x = directions[d]
                        nv = int(target.PrevState["Pv"]*windmap[y][x])
                        if self.State["Pv"] < nv: self.State["Pv"] = nv

    def distancewave(self, zero=False):
        if zero:
            if self.PrevState["BoarderWaveType"] != 0 and self.PrevState["BoarderWaveType"] == self.State["BoarderWaveType"]:
                self.State["BoarderWaveType"] = 0
            self.State["BoarderWaveHistory"] = [0, 0, 1]

            if self.PrevState["DeparterWaveType"] != 0 and self.PrevState["DeparterWaveType"] == self.State["DeparterWaveType"]:
                self.State["DeparterWaveType"] = 0
            self.State["DeparterWaveHistory"] = [0, 0, 1]

            self.State["CanSpawn"] = True
        else:

            if self.State["BoarderWaveType"] > 6:
                self.State["BoarderWaveType"] -= 1
                if self.State["BoarderWaveType"] == 6:
                    self.State["BoarderWaveType"] = 0
                    self.State["DeparterWaveType"] = 5
                return()

            (l, r, u, d) = (self.neighbours.lookup("L"), self.neighbours.lookup("R"), self.neighbours.lookup("U"), self.neighbours.lookup("D"))

            #1 = upwards travelling cell
            #2 = downwards travelling cell
            #3 = rightwards travelling cell
            #4 = leftwards travelling cell
            #5 = full source cell
            #6 = lr source cell
            (lprev, rprev, uprev, dprev) = (0 if not l else l.PrevState["BoarderWaveType"],
                                            0 if not r else r.PrevState["BoarderWaveType"],
                                            0 if not u else u.PrevState["BoarderWaveType"],
                                            0 if not d else d.PrevState["BoarderWaveType"])
            
            if (uprev in [2, 5, 10]) and (dprev in [1, 5, 10]):
                self.State["BoarderWaveType"] = 5
                self.State["BoarderWaveHistory"][0] = 1
                self.State["CanSpawn"] = False
            elif uprev in [2, 5, 10]:
                self.State["BoarderWaveType"] = 2
                self.State["BoarderWaveHistory"][0] = 1
                self.State["CanSpawn"] = False
            elif dprev in [1, 5, 10]:
                self.State["BoarderWaveType"] = 1
                self.State["BoarderWaveHistory"][0] = 1
                self.State["CanSpawn"] = False
            else:
                if (lprev in [1,2,3,5,6,10]) and rprev in ([1,2,4,5,6,10]):
                    self.State["BoarderWaveType"] = 6
                    self.State["BoarderWaveHistory"][0] = 1
                    self.State["CanSpawn"] = False
                elif lprev in [1,2,3,5,6,10]:
                    self.State["BoarderWaveType"] = 3
                    self.State["BoarderWaveHistory"][0] = 1
                    self.State["CanSpawn"] = False
                elif rprev in [1,2,4,5,6,10]:
                    self.State["BoarderWaveType"] = 4
                    self.State["BoarderWaveHistory"][0] = 1
                    self.State["CanSpawn"] = False
                else:
                    if self.State["BoarderWaveType"] != 0:
                        self.State["BoarderWaveType"] = 0


            if self.State["DeparterWaveType"] > 6:
                self.State["DeparterWaveType"] -= 1
                if self.State["DeparterWaveType"] == 6:
                    self.State["DeparterWaveType"] = 0
                    self.State["BoarderWaveType"] = 5
                return()

            #1 = upwards travelling cell
            #2 = downwards travelling cell
            #3 = rightwards travelling cell
            #4 = leftwards travelling cell
            #5 = full source cell
            #6 = lr source cell
            (lprev, rprev, uprev, dprev) = (0 if not l else l.PrevState["DeparterWaveType"],
                                            0 if not r else r.PrevState["DeparterWaveType"],
                                            0 if not u else u.PrevState["DeparterWaveType"],
                                            0 if not d else d.PrevState["DeparterWaveType"])
            
            if (uprev in [2, 5, 9]) and (dprev in [1, 5, 9]):
                self.State["DeparterWaveType"] = 5
                self.State["DeparterWaveHistory"][0] = 1
                self.State["CanSpawn"] = False
            elif uprev in [2, 5, 9]:
                self.State["DeparterWaveType"] = 2
                self.State["DeparterWaveHistory"][0] = 1
                self.State["CanSpawn"] = False
            elif dprev in [1, 5, 9]:
                self.State["DeparterWaveType"] = 1
                self.State["DeparterWaveHistory"][0] = 1
                self.State["CanSpawn"] = False
            else:
                if (lprev in [1,2,3,5,6,10]) and rprev in ([1,2,4,5,6,10]):
                    self.State["DeparterWaveType"] = 6
                    self.State["DeparterWaveHistory"][0] = 1
                    self.State["CanSpawn"] = False
                elif lprev in [1,2,3,5,6,10]:
                    self.State["DeparterWaveType"] = 3
                    self.State["DeparterWaveHistory"][0] = 1
                    self.State["CanSpawn"] = False
                elif rprev in [1,2,4,5,6,10]:
                    self.State["DeparterWaveType"] = 4
                    self.State["DeparterWaveHistory"][0] = 1
                    self.State["CanSpawn"] = False
                else:
                    if self.State["DeparterWaveType"] != 0:
                        self.State["DeparterWaveType"] = 0

    # ==============================================================================================================================#
    # person updating ruleset

    def PersonMove(self):
        for d in ["L", "R", "U", "D", "UL", "UR", "DL", "DR"]:
            target = self.neighbours.lookup(d)
            if target and target.PrevState["PersonDir"] == d:
                self.typ = target.PrevState["PersonType"]
                if target.PrevState["PersonType"] == 5: self.State["BoarderWaveType"] = 10
                else: self.State["DeparterWaveType"] = 10
                
                self.State["Carrier"] = target.PrevState["Carrier"]
                self.State["Infection"] = target.PrevState["Infection"]
                if not self.State["Infection"]:
                    chance = random.randint(1, 100)
                    if chance < int(self.State["Pv"]*100/30):
                        self.State["Infection"] = True
                        
                self.State["CanSpawn"] = False
                self.updated = True
                break

    def PersonNavigation(self):
        """Outer function controlling person navigation, includes the despawn conditions."""
        ai = self.typ - 4
        
        # despawn rules
        if (ai == 1 and self.prevtyp == 4) or (ai in [2, 3] and self.prevtyp == 3):
            if self.prevtyp == 4:
                self.typ = self.prevtyp
                self.updated = True
                return()
        
        elif (ai == 4 and self.x == 219) or (ai == 5 and self.x == 0):
                self.typ, self.prevtyp = 3, 3
                self.updated = True
                return()
            
        # movement
        self.move_person(ai)

    def move_person(self, ai):
        """Functionality handling how people move. First, tiles are tested in decreasing preference order."""
        """subsequently, motion is made in the optimal direction."""
        bestd = ""
        mini = self.getheat(ai)
        prefs = direction_preferences(ai)

        for pd in prefs:
            t = self.test_tile(pd, ai)
            if t < mini or (t == mini and bestd == ""):
                mini = t
                bestd = pd

        if ai == 1: self.State["BoarderWaveType"] = 10
        else: self.State["DeparterWaveType"] = 10
        self.State["CanSpawn"] = False

        if bestd != "":
            self.State["PersonType"] = self.typ
            self.State["PersonDir"] = reciprocals[bestd]
            self.typ = self.prevtyp
            self.updated = True

    def test_tile(self, d, ai):
        """Functionality for obtaining the heatmap value of a tile in the given direction of motion."""
        target = self.neighbours.lookup(d)
        if target: return(target.getheat(ai))
        else: return(10000000)

    def getheat(self, ai):
        """function for obtaining heat value for the current tile."""
        w1, w2 = self.weights[ai-1]
        # value from boarder distance waves
        v1 = (0 if not 1 in self.PrevState["BoarderWaveHistory"] else self.historylength-self.PrevState["BoarderWaveHistory"][::-1].index(1) + 1)
        # value from other people distance waves
        v2 = (0 if not 1 in self.PrevState["DeparterWaveHistory"] else self.historylength-self.PrevState["DeparterWaveHistory"][::-1].index(1) + 1)
        return(self.initialheat[ai-1] + w1*v1 + w2*v2)

    # ==============================================================================================================================#
    # person spawn ruleset
    
    def SpawnPeople(self, tick):
        """Function for spawning people."""
        # entrance tile spawning rules
        if self.typ == 3:
            
            if self.x < 5 and self.y == 30:                     # left entrance
                target = self.neighbours.lookup("R")
                if target.PrevState["CanSpawn"]:

                    chance = random.randint(1, 100)
                    if chance <= 5:             # 5% chance of spawning boarder
                        self.spawn_person("R", 5)
                    elif chance <= 7:            # 2% chance of spawning right walker
                        self.spawn_person("R", 8)

            elif self.x > 215 and self.y == 30:                 # right entrance
                target = self.neighbours.lookup("L")
                if target.PrevState["CanSpawn"]:

                    chance = random.randint(1, 100)
                    if chance <= 5:             # 5% chance of spawning boarder
                        self.spawn_person("L", 5)
                    elif chance <= 7:            # 2% chance of spawning left walker
                        self.spawn_person("L", 9)
                        
            elif self.y < 0 and self.x == 25 or self.x == 195:  # upper entrances
                target = self.neighbours.lookup("D")
                if target.PrevState["CanSpawn"]:

                    chance = random.randint(1, 100)
                    if chance <= 5:              # 5% chance of spawning boarder
                        self.spawn_person("D", 5)

        # exit tile spawning rules
        if self.typ == 4:
            if self.x == 110:
                target = self.neighbours.lookup("U")
                if target.PrevState["CanSpawn"]:

                    chance = random.randint(1, 100)
                    if chance <= 5: # 5% chance of spawning a departer of each type
                        self.spawn_person("U", 6)
                    elif chance <= 10:
                        self.spawn_person("U", 7)
                        
            

    def spawn_person(self, d, typ):
        self.State["PersonType"] = typ
        self.State["PersonDir"] = reciprocals[d]
        if random.randint(0, 1) == 0:
            self.State["Infection"], self.State["Carrier"] = True, True
        else:
            self.State["Infection"], self.State["Carrier"] = False, False

    # ==============================================================================================================================#
    # overall update ruleset

    def UpdateRules(self, tick, windmap):
        """Function controlling the update rules."""
        subtick = round(tick*TICKSIZE) % TICKSIZE
        if self.typ != 0:
            self.SpreadTiles(windmap)                   # pv spread
            # motion frames
            if subtick == 8:
                self.distancewave(True)                 # zero out distancing spread
                
                if (self.typ == 3 or self.typ == 4) and round(tick) % 4 == 0:
                    self.SpawnPeople(tick)              # on every 4th motion frame, attempt spawning

                if self.typ in [5,6,7,8,9]:
                    self.PersonNavigation()             # have people plan navigation

            # motion frames
            elif subtick == 0:
                self.PersonMove()                       # move people
                
            else:
                self.distancewave()                     # distancing spread

    # ==============================================================================================================================#
    # visuals and post-processing update

    def UpdateVisuals(self, tick, windmap):
        """Routine for updating tiles. Controls the periodic arrival of buses, as well as spread of pathogens."""
        self.PrevState = self.State
        self.State = self.PrevState.copy()
        
        self.State["Pv"] = int(self.PrevState["Pv"]*windmap[1][1])
        self.State["PersonType"], self.State["PersonDir"] = None, None
        self.State["BoarderWaveHistory"] = ([0] + self.PrevState["BoarderWaveHistory"][:(self.historylength-1)])
        self.State["DeparterWaveHistory"] = ([0] + self.PrevState["DeparterWaveHistory"][:(self.historylength-1)])

        # manage opening/closing of bus stop exit tiles
        if self.prevtyp == 2:
            if tick % 600 == 500:
                self.typ = 4
                self.prevtyp = 4
                self.updated = True
                pygame.draw.rect(self.screen, self.colourtile(self.typ), self.rect, 1)
        elif self.prevtyp == 4:
            if tick % 600 == 1:
                self.typ = 2
                self.prevtyp = 2
                self.updated = True
                pygame.draw.rect(self.screen, self.colourtile(self.typ), self.rect)#, 1)

        # update appearance if told to
        if self.updated:
            pygame.draw.rect(self.screen, self.colourtile(self.typ), self.rect)#, 1)
            self.updated = False

        # or if state values suggest we should
        if self.typ != 0:
            if self.PrevState["Pv"] > 0 or self.PrevState["BoarderWaveHistory"] != self.State["BoarderWaveHistory"] or self.PrevState["DeparterWaveHistory"] != self.State["DeparterWaveHistory"]:
                pygame.draw.rect(self.screen, self.colourtile(self.typ), self.rect)#, 1)
                
    def colourtile(self, typ):
        """function for getting tile colour based on tile type."""
        if typ == 1:
            return(self.shadeinred(self.colourmap[self.x]))
        elif typ in [0, 2]:
            return(self.colours[typ])
        else:
            if typ in [5,6,7,8,9] and self.State["Carrier"]:
                return((255,0,0))
            elif typ in [5,6,7,8,9] and self.State["Infection"]:
                return((255,255,0))
            else:
                return(self.shadeinred(self.colours[typ]))

    def shadeinred(self, col):
        """function for shading tiles, will be based on Pv, but currently displays distancing metric."""
        (r, g, b, a) = col

        Pv1 = self.State["Pv"]/30
        Pv2 = (0 if not 1 in self.State["DeparterWaveHistory"] else self.historylength - self.State["DeparterWaveHistory"][::-1].index(1) + 1)/8
        Pv3 = (0 if not 1 in self.State["BoarderWaveHistory"] else self.historylength - self.State["BoarderWaveHistory"][::-1].index(1) + 1)/8

        n1 = int((255-r)*(1 - (1 - Pv1)**4))
        n2 = int((255-g)*Pv2)
        n3 = int((255-b)*Pv3)

        return((r+n1,g+n2,b+n3,a))

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
        self.colours = ["invisible",                                                # wall - not rendered to save on processing
                        "spec",                                                     # air - coloured specially based on the gradient generated below
                        pygame.Color("red"),                                        # closed exit - coloured red
                        pygame.Color("gold"),                                       # entrance - coloured gold
                        pygame.Color("green"),                                      # open exit - coloured green
                        pygame.Color("blue"),                                       # boarder - coloured blue
                        pygame.Color("light green"), pygame.Color("light green"),   # departer - coloured light green
                        pygame.Color("orange"), pygame.Color("orange")]             # walkers (both directions) - coloured orange

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

            subtick = round(self.tick*TICKSIZE) % TICKSIZE
            if not subtick == 8: self.perlincount += 1
            if subtick == 0: print(self.tick)

            # increment tick count
            self.tick += 1/TICKSIZE

            # CA update
            self.update_tileset()

            pygame.display.update()

            self.clock.tick(240)
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
