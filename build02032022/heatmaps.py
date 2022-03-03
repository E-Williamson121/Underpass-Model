class HeatMap():
    """Heatmap class. By default, has functionality for producing a zero heatmap."""
    def zero_map(self):
        """Produce a zero heatmap (2D array of zeroes)"""
        for y in range(0, self.height):
            row = []
            for x in range(0, self.width):
                row.append(0)
            self.map.append(row)
        
    def __init__(self, width, height):
        """Default attributes are width, height, and (empty) heatmap data."""
        self.width = width
        self.height = height
        self.map = []


def add_circle(tilemap, n, x, y, width, height, scale, social_dist, remove = False, spawnrem = False):
    """Produces a manhattan circle of either 2m or 0.75m around the given tile, the amplitude of the circle may be scaled."""
    radius = 8 if social_dist else 3
    if remove: tilemap[y][x].increases[n].remove(100)
    else: tilemap[y][x].increases[n].append(100)
    for dy in range(-radius, radius + 1):
        place_y = y + dy
        dx = abs(dy) - radius
        while dx < radius + 1 - abs(dy):
            place_x = x + dx
            if (place_y > -1 and place_y < height) and (place_x > -1 and place_x < width):
                if remove: tilemap[place_y][place_x].increases[n].remove(scale*(radius - (abs(place_x - x) + abs(place_y - y))))
                else: tilemap[place_y][place_x].increases[n].append(scale*(radius - (abs(place_x - x) + abs(place_y - y))))
            dx += 1

def addmaps(mapa, mapb):
    """Utility function for element-wise addition of two heatmaps of the same size."""
    s = [ map(lambda u, v: u + v, x, y) for (x, y) in zip(mapa, mapb) ]
    return( list(map(list, s)))


class BoardingMap(HeatMap):
    """Special class for the heatmap for boarding passengers."""
    def boarding_map(self):
        """The heatmap for boarding encourages straight line motion in corridors, and direct motion towards the exit when in range."""
        for y in range(0, self.height):
            row = []
            for x in range(0, self.width):
                if y < 21 and ((x > 9 and x < 36) or (x > 183 and x < 210)): row.append(100+self.height-y)
                elif y < 21 and (x < 10 or (x > 35 and x < 184) or x > 209): row.append(1000000)
                elif y > 20 and (x < 10 or x > 209): row.append(20+abs((self.width/2)-x))
                elif y > 20: row.append(abs((self.width/2)-x)+abs(self.height-y))
            self.map.append(row)

class DepartingMap(HeatMap):
    """Special class for the heatmap for departing passengers."""
    def departing_map(self):
        """Effectively the same heatmap as that in BoardingMap class, but numbers are subtracted so that the profile is reversed."""
        for y in range(0, self.height):
            row = []
            for x in range(0, self.width):
                if y < 21 and ((x > 9 and x < 36) or (x > 183 and x < 210)): row.append(140-(100+self.height-y))
                elif y < 21 and (x < 10 or (x > 35 and x < 184) or x > 209): row.append(1000000)
                elif y > 20 and (x < 10 or x > 209): row.append(140-(20+abs((self.width/2)-x)))
                elif y > 20: row.append(140-(abs((self.width/2)-x)+abs(self.height-y)))
            self.map.append(row)

class LRMap(HeatMap):
    """Class for heatmaps which assure travel from left to right on the main corridor."""
    def right_map(self):
        """Heatmap which travels moving right (increasing from 0 to 220)."""
        for y in range(0, self.height):
            row = []
            for x in range(0, self.width):
                if y < 21: row.append(1000000)
                else: row.append(x)
            self.map.append(row)

    def left_map(self):
        """Heatmap which travels moving left (decreasing from 220 to 0)"""
        for y in range(0, self.height):
            row = []
            for x in range(0, self.width):
                if y < 21: row.append(1000000)
                else: row.append(self.width-x)
            self.map.append(row)

class BaseMaps():
    """Class of base versions of maps prior to modification, useful for exporting."""
    def __init__(self):
        self.boarding = BoardingMap(220, 40)
        self.boarding.boarding_map()

        self.departing = DepartingMap(220, 40)
        self.departing.departing_map()

        self.left = LRMap(220, 40)
        self.left.left_map()

        self.right = LRMap(220, 40)
        self.right.right_map()

        self.zero = HeatMap(220, 40)
        self.zero.zero_map()

Base = BaseMaps()
