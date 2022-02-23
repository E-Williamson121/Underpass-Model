class BlockPool():
    def __init__(self, n, scale, canvas):
        self.Pool = []
        for i in range(0, n):
            sq = Block(scale, self, canvas)
            self.Pool.append(sq)

    def set_active(self):
        if self.Pool:
            first, self.Pool = self.Pool[0], self.Pool[1:]
            return first
        else:
            return None

    def set_inactive(self, sq):
        self.Pool.append(sq)


class Block():
    def __init__(self, size, pool, canvas):
        self.pool = pool
        self.canvas = canvas
        self.x = 0
        self.y = 0
        self.col = None
        self.out = None
        self.scale = size
        self.visual = self.canvas.create_rectangle(0,0,0,0,
                                                   outline="", fill="black",
                                                   state="hidden")
    def despawn(self):
        self.canvas.itemconfigure(self.visual, state="hidden")
        self.pool.set_inactive(self)

    def spawn(self, x, y, col, outline=None):
        self.x, self.y, self.col, self.out = x, y, col, outline
        if not outline:
            self.canvas.coords(self.visual, x*self.scale, y*self.scale,
                                      (x+1)*self.scale, (y+1)*self.scale)
            self.canvas.itemconfigure(self.visual, fill=col, state="normal")
        else:
            self.canvas.coords(self.visual, x*self.scale, y*self.scale,
                                      (x+1)*self.scale, (y+1)*self.scale)
            self.canvas.itemconfigure(self.visual, fill=col, outline=outline, state="normal")


    def move(self, nx, ny):
        if self.x != nx or self.y != ny:
            self.x, self.y = nx, ny
            self.canvas.coords(self.visual, nx*self.scale, ny*self.scale,
                               (nx+1)*self.scale, (ny+1)*self.scale)

    def recolour(self, ncol, nout=None):
        if not nout:
            if self.col != ncol:
                self.col = ncol
                self.canvas.itemconfigure(self.visual, fill=ncol)
        else:
            if self.col != ncol or self.out != nout:
                self.col, self.out = ncol, nout
                self.canvas.itemconfigure(self.visual, fill=ncol, outline=nout)
