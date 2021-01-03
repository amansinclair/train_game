import random
from itertools import cycle
from pathlib import Path

import pyglet


class Person:
    def __init__(self, sprite, x1, y1, x2, y2, at_station_one=True):
        self.sprite = sprite
        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2
        self.at_station(at_station_one)

    def in_train(self):
        self.sprite.visible = False

    def at_station(self, at_station_one=True):
        self.sprite.visible = True
        if at_station_one:
            self.sprite.x = self.x1
            self.sprite.y = self.y1
        else:
            self.sprite.x = self.x2
            self.sprite.y = self.y2


class Track:
    def __init__(self, width, y_low=96, y_high=407, station_one=None, station_two=None):
        self.width = width
        self.y_low = y_low
        self.y_high = y_high
        self.station_one = station_one if station_one else []
        self.station_two = station_two if station_two else []
        self.in_train = []
        self.picking_up = True

    def update(self, dt, train):
        if train.speed == 0:
            if train.pos > 0.3 and train.pos < 0.4:
                if self.pickup(dt):
                    self.exchange_passenger(train, self.station_one, True)
            elif train.pos > 0.8 and train.pos < 0.9:
                if self.pickup(dt):
                    self.exchange_passenger(train, self.station_two, False)
        else:
            self.count = 0
            self.next_pass = 0.5
            self.picking_up = self.set_pickup_mode()

    def pickup(self, dt=0):
        if dt:
            self.count += dt
            if self.count > self.next_pass:
                self.next_pass += 0.5
                return True
        return False

    def exchange_passenger(self, train, station, at_station_one):
        if station and self.picking_up:
            passenger = station.pop(random.randrange(len(station)))
            passenger.in_train()
            self.in_train.append(passenger)
        elif not self.picking_up and self.in_train:
            passenger = self.in_train.pop(random.randrange(len(self.in_train)))
            passenger.at_station(at_station_one)
            station.append(passenger)

    def set_pickup_mode(self):
        if not (self.in_train):
            return True
        elif not (self.station_one) and not (self.station_two):
            return False
        else:
            return self.picking_up

    def convert_pos(self, train):
        pos = train.pos
        w = train.width
        if pos <= 0.5:
            x = self.width - (pos * 2 * (self.width + w))
            y = self.y_low
            left = True
        else:
            x = (pos * 2 * (self.width + w)) - (self.width + (2 * w))
            y = self.y_high
            left = False
        return x, y, left


class Train:

    max_speed = 0.1
    acc_scale = 0.2
    dec_scale = 0.05
    length = 0.124

    def __init__(self, res_dict, track):
        self.speed = 0
        self.pos = 0.12
        self.is_active = False
        self.res_dict = res_dict
        self.width = res_dict["left"].width
        self.track = track
        self.sound_player = pyglet.media.Player()
        self.update(0)

    def pedal_down(self):
        self.is_active = True
        if not self.sound_player.playing:
            self.sound_player.queue(self.res_dict["tootoo"])
            self.sound_player.play()

    def pedal_up(self):
        self.is_active = False

    def accel(self, dt):
        self.speed = min(self.max_speed, self.speed + (dt * self.acc_scale))

    def deccel(self, dt):
        self.speed = max(0, self.speed - (dt * self.dec_scale))

    def update(self, dt):
        if self.is_active:
            self.accel(dt)
        else:
            self.deccel(dt)
        self.pos = (self.pos + (self.speed * dt)) % 1
        x, y, left = self.track.convert_pos(self)
        if left:
            self.sprite = self.res_dict["left"]
        else:
            self.sprite = self.res_dict["right"]
        self.sprite.x, self.sprite.y = x, y


class Animals:
    def __init__(self, res, v=15, y_top=450, y_bot=200):
        self.res = res
        self.v = v
        self.y = y_top
        self.y_top = y_top
        self.y_bot = y_bot
        self.rest(y_top)

    def move(self):
        if self.y == self.y_top:
            self.move_down()
        elif self.y == self.y_bot:
            self.move_up()

    def move_down(self):
        self.state = "animals_down"
        self.sprite = pyglet.sprite.Sprite(
            img=self.res[self.state], x=800, y=self.y_top
        )

    def move_up(self):
        self.state = "animals_up"
        self.sprite = pyglet.sprite.Sprite(
            img=self.res[self.state], x=800, y=self.y_bot
        )

    def rest(self, y):
        self.state = "animals"
        self.sprite = pyglet.sprite.Sprite(img=self.res[self.state], x=800, y=y)

    def update(self, dt):
        if self.state == "animals_down":
            self.y = max(self.y - (dt * self.v), self.y_bot)
            self.sprite.y = int(round(self.y))
            if self.y == self.y_bot:
                self.rest(self.y_bot)
        elif self.state == "animals_up":
            self.y = min(self.y + (dt * self.v), self.y_top)
            self.sprite.y = int(round(self.y))
            if self.y == self.y_top:
                self.rest(self.y_top)


class BoomGate:
    def __init__(self, res, animals, start=0.55, finish=0.65, closed_time=5):
        self.res = res
        self.animals = animals
        self.start = start
        self.finish = finish
        self.state_iter = cycle(
            [("boom_open", 30), ("boom_down", 8), ("boom_closed", 6), ("boom_up", 8)]
        )
        self.state, self.next_event = next(self.state_iter)
        self.sprite = pyglet.sprite.Sprite(img=self.res[self.state], x=700, y=408)
        self.t = 26.0
        self.closed_time = closed_time

    def update(self, dt, train):
        self.t += dt
        if self.t > self.next_event:
            self.move_gate(train)
        if self.state != "boom_open":
            self.slow_train(train)

    def train_in_way(self, train):
        return bool(train.pos > self.finish and train.pos < 0.8)

    def move_gate(self, train):
        if not (self.state == "boom_open" and self.train_in_way(train)):
            self.state, next_time = next(self.state_iter)
            if self.state == "boom_down" or self.state == "boom_up":
                self.animals.move()
            self.res["dingding"].play()
            self.next_event += next_time
            self.sprite = pyglet.sprite.Sprite(img=self.res[self.state], x=700, y=408)
        else:
            self.next_event += 5

    def slow_train(self, train):
        if train.pos > self.start and train.pos < self.finish:
            max_speed = (
                (self.finish - train.pos) / (self.finish - self.start)
            ) * train.max_speed
            train.speed = min(train.speed, max_speed)
            if train.pos + 0.001 > self.finish:
                train.is_active = False


class App(pyglet.window.Window):
    def __init__(self, app_path, H=1080, W=1920):
        super().__init__(W, H, fullscreen=False)
        pyglet.gl.glClearColor(0.1, 0.1, 0.1, 1)
        self.height = H
        self.width = W
        self.app_path = app_path
        (
            train_res,
            people_res,
            station_one,
            station_two,
            boom_res,
            animal_res,
        ) = self.load_resources()
        self.start_game(
            train_res, people_res, boom_res, animal_res, station_one, station_two
        )

    def load_resources(self):
        rc_path = self.app_path / "train_game" / "rc"
        train_res = {}
        for name in ("left", "right"):
            img = pyglet.image.load(rc_path / f"train_{name}.png")
            train_res[name] = pyglet.sprite.Sprite(img=img)
        bg_img = pyglet.image.load(rc_path / "bg.png")
        self.bg_sprite = pyglet.sprite.Sprite(img=bg_img, x=0, y=0)
        train_res["tootoo"] = pyglet.media.load(rc_path / "tootoo.wav", streaming=False)
        tunnel_img = bg_img = pyglet.image.load(rc_path / "tunnel.png")
        self.tunnels = pyglet.graphics.Batch()
        self.up_tunnel = pyglet.sprite.Sprite(
            img=tunnel_img, x=0, y=400, batch=self.tunnels
        )
        self.low_tunnel = pyglet.sprite.Sprite(
            img=tunnel_img, x=0, y=88, batch=self.tunnels
        )
        people_res = {}
        people_imgs = [f for f in rc_path.iterdir() if "p_" in f.stem]
        n_people = len(people_imgs)
        x_low = [x for x in range(250, 850, (850 - 250) // n_people)]
        random.shuffle(x_low)
        x_high = [x for x in range(1180, 1800, (1800 - 1180) // n_people)]
        random.shuffle(x_high)
        station_one = []
        station_two = []
        y_low = 110
        y_high = 426
        self.people = pyglet.graphics.Batch()
        for p, x_l, x_h in zip(people_imgs, x_low, x_high):
            img = pyglet.image.load(p)
            people_res[p.stem] = pyglet.sprite.Sprite(img=img, batch=self.people)
            if random.choice((True, False)):
                station_one.append(
                    Person(people_res[p.stem], x_l, y_low, x_h, y_high, True)
                )
            else:
                station_two.append(
                    Person(people_res[p.stem], x_l, y_low, x_h, y_high, False)
                )
        boom_res = {}
        for name, columns, loop in (
            ("boom_open", 1, False),
            ("boom_closed", 2, True),
            ("boom_up", 8, False),
            ("boom_down", 8, False),
        ):
            sprite_sheet = pyglet.image.load(rc_path / (name + ".png"))
            image_grid = pyglet.image.ImageGrid(sprite_sheet, rows=1, columns=columns)
            ani = pyglet.image.Animation.from_image_sequence(
                image_grid, duration=1.0, loop=loop
            )
            boom_res[name] = ani
        boom_res["dingding"] = pyglet.media.load(
            rc_path / "dingding.wav", streaming=False
        )
        animal_res = {}
        animal_res["animals"] = pyglet.image.load(rc_path / ("animals" + ".png"))
        for name in ("animals_up", "animals_down"):
            sprite_sheet = pyglet.image.load(rc_path / (name + ".png"))
            image_grid = pyglet.image.ImageGrid(sprite_sheet, rows=1, columns=2)
            ani = pyglet.image.Animation.from_image_sequence(
                image_grid, duration=0.5, loop=True
            )
            animal_res[name] = ani
        return train_res, people_res, station_one, station_two, boom_res, animal_res

    def start_game(
        self, train_res, people_res, boom_res, animal_res, station_one, station_two
    ):
        self.track = Track(self.width, station_one=station_one, station_two=station_two)
        self.train = Train(train_res, self.track)
        self.animals = Animals(animal_res)
        self.boom = BoomGate(boom_res, self.animals)
        pyglet.clock.schedule_interval(self.update, 1 / 120.0)

    def on_draw(self):
        self.clear()
        self.bg_sprite.draw()
        self.boom.sprite.draw()
        self.animals.sprite.draw()
        self.people.draw()
        self.train.sprite.draw()
        self.tunnels.draw()

    def update(self, dt):
        self.track.update(dt, self.train)
        self.boom.update(dt, self.train)
        self.animals.update(dt)
        self.train.update(dt)

    def on_key_press(self, symbol, modifiers):
        if symbol == 32:
            self.train.pedal_down()

    def on_key_release(self, symbol, modifiers):
        if symbol == 32:
            self.train.pedal_up()

    def run(self):
        pyglet.app.run()

    def __repr__(self):
        return "TrainGame()"


def run():
    game = App(Path.cwd())
    game.run()


if __name__ == "__main__":
    run()
