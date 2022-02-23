import random, heatmaps

class Person():
    """Person class, handles the functionality and movement AI of simulated people."""
    def __init__(self, x, y, app, inf, AI):
        """People have x and y coordinates, as well as booleans indicating their despawn locations."""
        self.x = x
        self.y = y
        self.col = "green"
        self.AI = AI
        self.infected = False
        self.carrier = (False if random.randint(0, 100) < 50 else True)
        
        self.prefdirs = []
        self.despawnsatexit = False
        self.despawnsatentrance = False
        self.despawned = False
        
        self.tiles = app.tileset
        self.height = app.height
        self.width = app.width
        self.distance = app.distance
        self.BlockPool = app.PersonPool

        self.weights = [[2,0.25,0.5,0.5],[0.25,1,0.5,0.5],[0.1,0.3,0.1,0.1],[0.1,0.3,0.1,0.1]]
        self.settile()
        self.add_circle()

    def add_circle(self):
        """Functionality for adding the circles of influence in each heatmap for a given person."""
        """(occurs upon spawn and at the end of movement)"""
        for i in range(0, 4):
            heatmaps.add_circle(self.tiles, i,
                                self.x, self.y,
                                self.width, self.height,
                                self.weights[i][self.AI], self.distance)

    def remove_circle(self):
        """Functionality for removing the circles of influence in each heatmap for a given person."""
        """(occurs at the start of movement calculations)."""
        for i in range(0, 4):
            heatmaps.add_circle(self.tiles, i,
                                self.x, self.y,
                                self.width, self.height,
                                self.weights[i][self.AI], self.distance, True)

    def despawn(self, isexit):
        """Functionality for despawning a person."""
        if (isexit and self.despawnsatexit) or (not isexit and self.despawnsatentrance):
            self.tiles[self.y][self.x].removeperson()
            self.despawned = True
            if self.displayitem:
                self.displayitem.despawn()
                self.displayitem = None
            #self.parent.canvas.delete(self.displayitem)
        
    def settile(self):
        """Functionality for moving a person onto a given tile."""
        self.tiles[self.y][self.x].addperson(self, self.col)

    def removetile(self):
        """Functionality for moving a person off of a given tile."""
        self.tiles[self.y][self.x].removeperson()

    def test_tile(self, d, tilemap):
        """Functionality for obtaining the heatmap value of a tile in the given direction of motion."""
        if d == "U": return (tilemap[self.y - 1][self.x].getheat(self.AI) if self.y > 0 else 10000000)
        elif d == "D": return (tilemap[self.y + 1][self.x].getheat(self.AI) if self.y < (self.height - 1) else 10000000)
        elif d == "R": return (tilemap[self.y][self.x + 1].getheat(self.AI) if self.x < (self.width - 1) else 10000000)
        elif d == "L": return (tilemap[self.y][self.x - 1].getheat(self.AI) if self.x > 0 else 10000000)
        elif d == "UR": return(tilemap[self.y - 1][self.x + 1].getheat(self.AI) if self.x < (self.width - 1) and self.y > 0 else 10000000)
        elif d == "UL": return(tilemap[self.y - 1][self.x - 1].getheat(self.AI) if self.x > 0 and self.y > 0 else 10000000)
        elif d == "DR": return(tilemap[self.y + 1][self.x + 1].getheat(self.AI) if self.x < (self.width - 1) and self.y < (self.height - 1) else 10000000)
        elif d == "DL": return(tilemap[self.y + 1][self.x - 1].getheat(self.AI) if self.x > 0 and self.y < (self.height - 1) else 10000000)

    def move(self):
        """Functionality handling how people move. First, tiles are tested in decreasing preference order, subsequently, motion is made in the optimal direction."""
        mini = self.tiles[self.y][self.x].getheat(self.AI)
        bestd = ""

        for pd in self.prefdirs:
            t = self.test_tile(pd, self.tiles)
            if t < mini or (t == mini and bestd == ""):
                mini = t
                bestd = pd

        if bestd != "":
            self.removetile()
            if bestd == "U": self.y -= 1
            elif bestd == "D": self.y += 1
            elif bestd == "L": self.x -= 1
            elif bestd == "R": self.x += 1
            elif bestd == "UR": self.x, self.y = self.x + 1, self.y - 1
            elif bestd == "UL": self.x, self.y = self.x - 1, self.y - 1
            elif bestd == "DR": self.x, self.y = self.x + 1, self.y + 1
            elif bestd == "DL": self.x, self.y = self.x - 1, self.y + 1
            if self.displayitem: self.displayitem.move(self.x, self.y)
            self.settile()

    def infection_chance(self):
        if random.randint(0, 100) < (self.tiles[self.y][self.x].Pv)*100:
            self.infected = True
            self.col = "yellow"
            if self.displayitem: self.displayitem.recolour(self.col, self.outlines[self.col])

    def update(self):
        """Update function handles motion and sets the person to despawn at the first exit/entrance they encounter (based on AI number)."""
        self.remove_circle()
        self.move()
        if not self.carrier and not self.despawned: self.infection_chance()
        if not self.despawned: self.add_circle()
        if not self.despawnsatexit and self.AI == 0: self.despawnsatexit = True
        if not self.despawnsatentrance and self.AI != 0: self.despawnsatentrance = True
            

class BoardingPerson(Person):
    """Class for people who are boarding a bus."""
    def __init__(self, x, y, parent, inf, entrance):
        """Movement preferences are variable depending on the spawn location relative to the bus stop."""
        super().__init__(x, y, parent, inf, 0)
        self.col = "blue"
        if self.carrier: self.col = "red"
        #self.make_displayitem()
        # left entrance
        if entrance == 1: self.prefdirs = ["R", "UR", "DR", "D", "U", "DL", "UL", "L"]
        # top-left entrance
        elif entrance == 2: self.prefdirs = ["D", "DR", "R", "UR", "U", "DL", "UL", "L"]
        # top-right entrance
        elif entrance == 3: self.prefdirs = ["D", "DL", "L", "UL", "U", "DR", "UR", "U"]
        # right entrance
        else: self.prefdirs = ["L", "UL", "DL", "D", "U", "DR", "UR", "R"]
        self.displayitem = self.BlockPool.set_active()
        self.outlines = {"orange" : "yellow", "yellow" : "gold", "red" : "pink", "blue" : "light blue", "green" : "light green"}
        if self.displayitem: self.displayitem.spawn(self.x, self.y, self.col, self.outlines[self.col])


class DepartingPerson(Person):
    """Class for people who are getting off of a bus."""
    def __init__(self, x, y, parent, inf):
        """Movement preference is mostly irrelevant, so chosen to be entirely random."""
        super().__init__(x, y, parent, inf, 1)
        self.col = "green"
        if self.carrier: self.col = "red"
        #self.make_displayitem()
        self.prefdirs = ["R", "UR", "DR", "D", "U", "DL", "UL", "L"]
        random.shuffle(self.prefdirs)
        while self.prefdirs[0] == "U": random.shuffle(self.prefdirs)
        self.displayitem = self.BlockPool.set_active()
        self.outlines = {"orange" : "yellow", "yellow" : "gold", "red" : "pink", "blue" : "light blue", "green" : "light green"}
        if self.displayitem: self.displayitem.spawn(self.x, self.y, self.col, self.outlines[self.col])


class LeftPerson(Person):
    """Class for people who are moving from left to right along the main corridor."""
    def __init__(self, x, y, parent, inf, left):
        """Movement preference is either Left-to-Right or Right-to-Left."""
        super().__init__(x, y, parent, inf, 2 + (0 if left else 1))
        self.left = left
        self.col = "orange"
        if self.carrier: self.col = "red"
        #self.make_displayitem()
        if not left: self.prefdirs = ["L", "DL", "UL", "D", "U", "UR", "DR", "R"]
        else: self.prefdirs = ["R", "UR", "DR", "D", "U", "DL", "UL", "L"]
        self.displayitem = self.BlockPool.set_active()
        self.outlines = {"orange" : "yellow", "yellow" : "gold", "red" : "pink", "blue" : "light blue", "green" : "light green"}
        if self.displayitem: self.displayitem.spawn(self.x, self.y, self.col, self.outlines[self.col])

