import threading
import time
import math
import tkinter as tk

from arena import EXIT, START, WALLS
from drone_api import DroneAPI

ARENA_W = 30.0   #m
ARENA_H = 30.0
SCALE = 20       #pixel per meter


class Game:
    def __init__(self, drone):
        self.drone = drone

    def forward_dist(self, dist, speed=1.0):
        p0 = self.drone.get_pose()
        while not self.drone.crashed:
            p = self.drone.get_pose()
            if math.hypot(p["x"] - p0["x"], p["y"] - p0["y"]) >= dist:
                break
            self.drone.move_vel(speed, 0.0, 0.0)
            time.sleep(0.02)
        self.drone.hover()
        time.sleep(0.5)

    def maze(self, speed=3.0, alt=2.0):
        self.drone.wait4start()
        self.drone.takeoff(alt)
        legs = [
            (6.0, 90.0),
            (16.0, -90.0),
            (6.0, -90.0),
            (10.0, 90.0),
            (8.0, 90.0),
            (8.0, 90.0),
            (4.0, None),
        ]
        for i, (dist, turn) in enumerate(legs, 1):
            print(f"[Maze] Leg {i}: forward {dist} m")
            self.forward_dist(dist, speed)
            if self.drone.crashed:
                print("[Maze] Crashed, mission aborted")
                return
            if turn is not None:
                print(f"[Maze] Turning {'left' if turn > 0 else 'right'} {abs(turn):.0f} deg")
                self.drone.move_yaw(turn, tol=0.1)
        self.drone.land()
        print("[Maze] Reached the exit, landed")

class ArenaView:
    def __init__(self, root, drone):
        self.drone = drone
        self.canvas = tk.Canvas(root, width=ARENA_W * SCALE, height=ARENA_H * SCALE, bg="white")
        self.canvas.pack()
        self.label = tk.Label(root, font=("Consolas", 11))
        self.label.pack()
        self._draw_grid()
        self._draw_maze()
        self._update()

    def to_px(self, x, y):
        return (ARENA_W / 2 + x) * SCALE, (ARENA_H / 2 - y) * SCALE

    def _draw_grid(self):
        for i in range(int(ARENA_W) + 1):
            self.canvas.create_line(i * SCALE, 0, i * SCALE, ARENA_H * SCALE, fill="#eee")
        for j in range(int(ARENA_H) + 1):
            self.canvas.create_line(0, j * SCALE, ARENA_W * SCALE, j * SCALE, fill="#eee")

    def _draw_maze(self):
        for a, b in WALLS:
            self.canvas.create_line(*self.to_px(*a), *self.to_px(*b), width=4, fill="#333")
        ex, ey = self.to_px(*EXIT)
        self.canvas.create_rectangle(ex - 15, ey - 15, ex + 15, ey + 15, outline="#2a6", width=2)
        self.canvas.create_text(ex, ey - 22, text="EXIT", fill="#2a6")

    def _update(self):
        self.canvas.delete("dyn")
        d = self.drone
        pose = d.get_pose()

        trail = [c for p in d.trail[::5] for c in self.to_px(*p)]
        if len(trail) >= 4:
            self.canvas.create_line(*trail, fill="#7aa", tags="dyn")

        cx, cy = self.to_px(pose["x"], pose["y"])
        r = 8
        color = "#d33" if d.crashed else ("#2a6" if d.armed else "#888")
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, tags="dyn")
        h = math.radians(pose["heading"])
        self.canvas.create_line(cx, cy, cx + 18 * math.cos(h), cy - 18 * math.sin(h),
                                width=3, arrow=tk.LAST, fill="red", tags="dyn")

        self.label.config(text=f"x={pose['x']:6.2f}  y={pose['y']:6.2f}  z={pose['z']:5.2f}  "
                               f"hdg={pose['heading']:6.1f}  mode={d.mode}  armed={d.armed}")
        self.canvas.after(30, self._update)


if __name__ == "__main__":
    drone = DroneAPI(x=START[0], y=START[1], heading=START[2], walls=WALLS)
    game = Game(drone)

    root = tk.Tk()
    root.title("EDRT 2D drone sim")
    ArenaView(root, drone)

    threading.Thread(target=game.maze, daemon=True).start()
    root.mainloop()
    drone.shutdown()
