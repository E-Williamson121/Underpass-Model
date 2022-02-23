import random

def smoothstep(v):
    """smoothstep function (used for lerp in perlin1d generator)"""
    if v <= 0: return(0)
    elif v >= 1: return(1)
    else: return(6*v**5 - 15*v**4 + 10*v**3)#return(3*v**2 - 2*v**3)

def perlin1d(x):
    """1D perlin noise generator (smooth random number generator, takes real number input)"""
    """Resolution of random values is 2dp (.01)."""
    x0 = int(x)
    x1 = x0 + 1

    random.seed(x0)
    v0 = random.randint(-101, 100)
    random.seed(x0 + 1)
    v1 = random.randint(-101, 100)

    dx = x - x0
    n0 = v0*0.01
    n1 = v1*0.01

    v = n0 + smoothstep(dx)*(n1 - n0)
    return(v)

## ====================== test code below ====================== ##
# test code displays two perlin noise generated curves
# the curve with red peaks is an unedited 1D perlin noise plot
# the curve with blue peaks is a 1D perlin noise value passed through a logistic/sigmoid curve mapping [-1, 1] to [-1, 1].
# the latter is useful in, for example, modelling wind, as direction change is smooth but steep, resulting in a "gusty" profile.

if __name__ == "__main__":
    def sigmoid(x):
        return(1/(1+math.exp(-x)))

    def moveleftlines():
        for line in lines:
            v = canvas.coords(line)
            if v[2] - xv < 0:
                canvas.delete(line)
                lines.remove(line)
            else:
                canvas.coords(line, v[0]-xv, v[1], v[2]-xv, v[3])
    
    def end(x):
        win.destroy()
        os._exit(0)
    
    import tkinter, time, os, math

    win = tkinter.Tk()

    win.title("Perlin Noise Test")
    win.resizable(False, False)
    win.geometry("480x360")
    win.configure(bg="black")
    win.bind("<Escape>", end)
            
    main = tkinter.Frame(win)
    main.pack(fill = "both", expand = 1)
            
    canvas = tkinter.Canvas(main, bg = "white")
    canvas.pack(fill = "both", expand = 1)
    fc = 1
    fc2 = random.randint(0, 10000000)
    dotfill = "black"
    dot = canvas.create_oval(100, 100, 105, 105, fill=dotfill, outline="")
    dotfill2 = "black"
    dot2 = canvas.create_oval(100, 100, 105, 105, fill=dotfill, outline="")
    lines = []
    y = 0
    y2 = 0
    xv = 5
    canvas.create_line(0, 0, 100, 0, width = 2, fill = "black")

    while True:

        prevy = y
        prevy2 = y2
        y = perlin1d(fc/15)
        perlinvalue = perlin1d(fc2/15)
        y2 = (sigmoid(4*(perlinvalue-1)) + sigmoid(4*(perlinvalue + 1)) - 1)/(sigmoid(1)-sigmoid(-1))

        if abs(y) > 0.5:
            if dotfill == "black":
                dotfill = "red"
                canvas.itemconfig(dot, fill=dotfill)
        else:
            if dotfill == "red":
                dotfill = "black"
                canvas.itemconfig(dot, fill=dotfill)

        if abs(y2) > 0.5:
            if dotfill2 == "black":
                dotfill2 = "blue"
                canvas.itemconfig(dot2, fill=dotfill2)
        else:
            if dotfill2 == "blue":
                dotfill2 = "black"
                canvas.itemconfig(dot2, fill=dotfill2)
        
        l = canvas.create_line(100-xv, 200 + prevy*100, 100, 200 + y*100, width = 2, fill=dotfill)
        l2 = canvas.create_line(100-xv, 200 + prevy2*100, 100, 200 + y2*100, width = 2, fill=dotfill2)
        lines.append(l)
        lines.append(l2)

        canvas.coords(dot, 100, 200 + y*100 - 2.5, 105, 200 + y*100 + 2.5)
        canvas.coords(dot2, 100, 200 + y2*100 - 2.5, 105, 200 + y2*100 + 2.5)

        win.update()
        moveleftlines()

        fc += 1
        fc2 += 1
        time.sleep(1/30)
        
