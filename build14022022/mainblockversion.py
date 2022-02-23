import tkinter, os, time, random, math, blocks, heatmaps, functools
import perlinnoise as perlin
import blockpeople as people

def sigmoid(x):
    return(1/(1+math.exp(-x)))

def set_windmap(value=0):
    # lateral wind direction is a [-1, 1] scalar value, this is translated into a weighted directional spread map.
    windmap = [[0.5-0.1*value, 0.5, 0.5+0.1*value],
               [0.5-0.2*value, 0.5, 0.5+0.2*value],
               [0.5-0.1*value, 0.5, 0.5+0.1*value]]
    return(windmap)


class Spreader():
    """Spreader class. Implements a breadth-first spreading algorithm for weighted radial spreading from sources."""
    def __init__(self, app):
        # some useful attribute settings, such as the tileset and tolerance value.
        self.tiles = app.tileset
        self.width = app.width
        self.height = app.height
        self.tol = app.tol

    def BFSSpread(self, x, y, windmap):
        """Breadth-first spreading algorithm. Spreads radially from a given x, y, based on parent windmap data."""
        
        # initialize breadth first spread
        self.Visited = []
        self.Queue = []
        self.tiles[y][x].Pv = 1

        # breadth first spread:
        # while the queue is non-empty, dequeue the front element and spread to its neighbours, before logging as visited.
        self.enqueue(x, y)
        while len(self.Queue) > 0:
            (y, x), self.Queue = self.Queue[0], self.Queue[1:]
            self.spreadtiles(x, y, windmap)
            self.Visited.append((y, x))

    def enqueue(self, x, y):
        """Enqueues a y-x tuple if the tuple is not already in the queue and has not been visited."""
        if not (y, x) in self.Queue and not (y, x) in self.Visited:
            self.Queue.append((y, x))

    def spreadtiles(self, x, y, windmap):
        """Algorithm for distributing spread to neighbour tiles."""
        # applies only if the current cell has a non-zero value (values below tolerance are effectively zero)
        if self.tiles[y][x].Pv > self.tol:
            # a useful constant for readability.
            Pv = self.tiles[y][x].Pv

            # set the Pvs of the surrounding cells based on the windmap.
            self.setpv(y-1, x-1, Pv*windmap[0][0])
            self.setpv(y, x-1, Pv*windmap[1][0])
            self.setpv(y+1, x-1, Pv*windmap[2][0])

            self.setpv(y-1, x, Pv*windmap[0][1])
            self.setpv(y+1, x, Pv*windmap[2][1])

            self.setpv(y-1, x+1, Pv*windmap[0][2])
            self.setpv(y, x+1, Pv*windmap[1][2])
            self.setpv(y+1, x+1, Pv*windmap[2][2])

    def setpv(self, ty, tx, nv):
        """Sets the Pv of the cell at (tx, ty) to nv if the current value is < nv, then enqueues the cell."""
        if tx > -1 and tx < self.width:
            if ty > -1 and ty < self.height:
                self.enqueue(tx, ty)
                if self.tiles[ty][tx].Pv < nv:
                    self.tiles[ty][tx].Pv = nv



class Tile():
    """Class for individual cells of the cellular automata, manages key events within these tiles."""
    def __init__(self, x, y, typ, app):
        """Initialization function, makes cell of a given type at a given position, by default tiles are uninhabited and exits are closed."""
        self.x   = x
        self.y   = y
        self.scale = app.scale

        self.initialheat = [heatmaps.Base.boarding.map[y][x],
                            heatmaps.Base.departing.map[y][x],
                            heatmaps.Base.left.map[y][x],
                            heatmaps.Base.right.map[y][x]]
        self.increases = [[0], [0], [0], [0]]
        
        self.Pv  = 0
        self.typ = typ
        if typ != 1: self.colour = app.colours[typ]
        else: self.colour = app.colourmap[self.x]
        self.tol = app.tol
        self.displayitem = None
        self.BlockPool = app.BlockPool

        self.person = None
        self.ExitOpen = False

        self.window = app.window

    def getheat(self, n):
        """function for obtaining heat value for the current tile."""
        return(round(self.initialheat[n] + max(self.increases[n]), 2))

    def shadeinred(self, col):
        """function for shading the current cell based on Pv value."""
        if self.Pv > 1: self.Pv = 1
        (r, g, b) = self.window.winfo_rgb(col)
        n = int((65534-r)*(1 - (1 - self.Pv)**2))
        return(("#%4.4x%4.4x%4.4x" % (r+n,g,b)))

    def colourtile(self, typ):
        """function for getting cell colour based on cell type."""
        return(self.shadeinred(self.colour))

    def removeperson(self):
        """Routine for (visually) removing a person from a tile."""
        self.person = None

    def addperson(self, dat, colour):
        """Routine for adding a person to a tile. If this tile is an exit or entrance, the person will trigger a relevant despawn routine."""
        self.person = dat
        if self.ExitOpen and self.typ == 2:
            dat.despawn(True)
        elif self.typ == 3:
            dat.despawn(False)

    def update(self, tick):
        """Routine for updating tiles. Controls the periodic arrival of buses, as well as spread of pathogens."""
        # control the bus stop exit opening/closing window
        if self.typ == 2:
            if tick % 600 == 1:
                self.ExitOpen = False
                self.colour = "red"
            elif tick % 600 == 499:
                self.colour = "green"
                self.ExitOpen = True
                if self.person and self.person.AI == 0:
                    self.person.remove_circle()
                    self.person.despawn(True)
                    self.person = None

        # update tile appearance based on Pv if needed
        if self.Pv > self.tol:
            self.Pv *= 0.7
            if self.typ != 0 and not self.person:
                if self.displayitem:
                    self.displayitem.recolour(self.colourtile(self.typ))
                else:
                    self.displayitem = self.BlockPool.set_active()
                    if self.displayitem:
                        self.displayitem.spawn(self.x, self.y, self.colourtile(self.typ))
            #self.Pv *= 0.001
        else:
            if self.Pv != 0:
                self.Pv = 0
                if self.typ != 0 and not self.person:
                    if self.displayitem:
                        self.displayitem.despawn()
                        self.displayitem = None

        return(self.person)


class Window():
    def end(self, e):
        """Utility function for clean program window exit."""
        self.window.destroy()
        #os._exit(0)

    # utility functions for detecting key presses/key releases.
    def processkey(self, e):
        if not e.keysym in self.keys:
            self.keys.append(e.keysym)

    def processrelease(self, e):
        if e.keysym in self.keys:
            self.keys.remove(e.keysym)


    def initialize_grid(self):
        """Function for creating underlying tile map for the grid. Currently the sizes and locations of corridors are hard-coded."""
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
        for y in range(0, self.height):
            row = []
            for x in range(0, self.width):
                row.append(Tile(x, y, self.grid[y][x], self))
            self.tileset.append(row)

    def updatetile(self, tile):
        person = tile.update(self.tick)
        if person: self.peoples[person.AI].append(person)

    def updateperson(self, person):
        person.update()
        if person.carrier: self.spreader.BFSSpread(person.x, person.y, self.wind)

    def update_tileset(self):
        """Update loop for all tiles on each tick."""
        # update people (and BFSSpread around any infected)
        list(map(lambda x: list(map(self.updateperson, x)), self.peoples))

        # flush storage of people, update tiles and store people found.
        self.peoples = [[],[],[],[]]             
        list(map(lambda x: list(map(self.updatetile, x)), self.tileset))
        
    def spawn_people(self):
        """Function for spawning new people."""        
        # spawn people randomly at entrances
        for i in range(0,4):
            if self.entrancecounts[i] == 0:
                # left entrance or right entrance
                if i == 0 or i == 3:
                    # small (20%) chance of spawning a walker
                    if random.randint(0, 100) < 20:
                        px, py = random.randrange(self.entrancex[2*i], self.entrancex[2*i+1]), random.randrange(self.entrancey[2*i], self.entrancey[2*i+1])
                        if not self.tileset[py][px].person: people.LeftPerson(px, py, self, False, self.entrancex[2*i] < 10)
                    
                    # 50% chance of spawning a boarder
                    elif random.randint(0, 100) < 50:
                        px, py = random.randrange(self.entrancex[2*i], self.entrancex[2*i+1]), random.randrange(self.entrancey[2*i], self.entrancey[2*i+1])
                        if not self.tileset[py][px].person: people.BoardingPerson(px, py, self, False, i + 1)

                # upper entrances
                else:
                    # 50% chance of spawning a boarder
                    if random.randint(0, 100) < 50:
                        px, py = random.randrange(self.entrancex[2*i], self.entrancex[2*i+1]), random.randrange(self.entrancey[2*i], self.entrancey[2*i+1])
                        if not self.tileset[py][px].person: people.BoardingPerson(px, py, self, False, i + 1)

                # set random delay to next spawn
                self.entrancecounts[i] = random.randint(30, 150)
                    
            else:
                self.entrancecounts[i] -= 1

        # if shortly following a bus arrival, trigger the disembarking of passengers.
        if (self.tick % 600) in range(500, 530):
            if self.departframe == 0:
                if self.departers > 0:
                    # 50% chance of spawning a departer
                    if random.randint(0, 100) < 50:
                        px, py = random.randrange(self.entrancex[8], self.entrancex[9]), random.randrange(self.entrancey[8], self.entrancey[9])
                        if not self.tileset[py][px].person: people.DepartingPerson(px, py, self, False)

                        # decrease the number of departers remaining and set a random delay.
                        self.departers -= 1
                        self.departframe = random.randint(5, 10)
                        
                        if self.departers == 0:
                            # bus may only depart after all passengers have disembarked.
                            self.tickincrease = True
                else:
                    self.tickincrease = True
            else:
                self.departframe -= 1


    def mainloop(self):
        """Main loop functionality for the program. Wind and people are updated first, then tile updates are propagated."""

        # update wind
        perlinvalue = self.perlin(self.perlincount/15)
        self.wind = set_windmap((2*sigmoid(1.5*(perlinvalue)) - 1)/(sigmoid(1)-sigmoid(-1)))
        self.perlincount += 1

        # spawn people
        self.spawn_people()

        # control tick count
        if self.tickincrease:
            self.tick += 1
            if self.tick % 600 == 500:
                self.departers = random.randint(3,8)
                self.departframe = 3
                self.tickincrease = False
                self.canvas.itemconfigure(self.busstop, fill="green")
            elif self.tick % 600 == 1:
                self.canvas.itemconfigure(self.busstop, fill="red")

        # update tiles
        self.update_tileset()

        self.window.after(30, lambda: self.mainloop())
        

    def __init__(self, height, width, scale):
        """Window initialization."""
        # attribute variables
        self.height = height
        self.width = width
        self.scale = scale
        self.distance = True    # variable for deciding if social distancing is enabled.

        # frameskip control and initial tick
        self.frameskip = False
        self.fpressed = False
        self.tickincrease = True
        self.tick = 0
        self.departers = 0
        self.departframe = 3
        self.tol = 0.05 # spread tolerance value
        self.peoples = [[],[],[],[]]

        # lists of entrance/exit data
        self.entrancex = [1,2,10,36,184,210,218,219,100,120]
        self.entrancey = [21,39,0,1,0,1,21,39,39,40]
        self.entrancecounts = [random.randint(30, 150), random.randint(30, 150), random.randint(30, 150), random.randint(30, 150)]

        # tk window properties
        self.window = tkinter.Tk()

        self.window.title("Grid Test")
        self.window.resizable(False, False)
        self.window.geometry("1200x250")
        
        self.keys = []
        self.window.bind("<KeyPress>", self.processkey)
        self.window.bind("<KeyRelease>", self.processrelease)
        self.window.bind("<Escape>", self.end)

        main           = tkinter.Frame(self.window)
        main.pack(fill = "both", expand = 1)
        
        self.canvas           = tkinter.Canvas(main, bg="black")
        self.canvas.pack(fill = "both", expand = 1)

        self.colours = ["invisible", "spec", "red", "gold"]
        self.colourmap = []
        
        for i in range(0, 110):
            n = int(150 - 100/110 * i)
            self.colourmap.append(("#%2.2x%2.2x%2.2x" % (n,n,n)))
        self.colourmap = self.colourmap + (self.colourmap[::-1])

        for x in range(0, self.width):
            self.canvas.create_rectangle(x*self.scale, 40*self.scale, (x+1)*self.scale,
                                         (21 if (x < 10 or (x > 35 and x < 184) or x > 209) else 0)*self.scale,
                                         fill=self.colourmap[x], outline="")
        self.canvas.create_rectangle(0, 40*self.scale, self.scale, 21*self.scale, fill="gold", outline="")
        self.canvas.create_rectangle(219*self.scale, 40*self.scale, 220*self.scale, 21*self.scale, fill="gold", outline="")
        self.canvas.create_rectangle(10*self.scale, 0, 36*self.scale, self.scale, fill="gold", outline="")
        self.canvas.create_rectangle(184*self.scale, 0, 210*self.scale, self.scale, fill="gold", outline="")
        
        self.busstop = self.canvas.create_rectangle(100*self.scale, 39*self.scale, 120*self.scale, 40*self.scale, fill="red", outline="")

        # block pool, total of 1080 blocks available for the program during execution
        self.BlockPool = blocks.BlockPool(1000, self.scale, self.canvas)
        self.PersonPool = blocks.BlockPool(80, self.scale, self.canvas)

        # main grid setup
        self.grid = []
        self.tileset = []

        self.initialize_grid()
        self.generate_display()

        # perlin noise
        self.perlincount = random.randint(0, 10000000) # seed randomly
        self.perlin = perlin.perlin1d

        # wind and spreader
        self.wind = set_windmap(self.perlin(self.perlincount/15))
        self.perlincount += 1

        self.spreader = Spreader(self)

        # begin mainloop
        self.window.after(30, lambda: self.mainloop())
        self.window.mainloop()


Window(40, 220, 5)
