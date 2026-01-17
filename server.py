import socket        # для мережевих з'єднань
import json          # для передачі стану гри у форматі JSON
import threading     # для багатопоточності (сервер + клієнти + м'яч)
import time          # для таймерів і затримок
import random        # для випадкового напрямку м'яча

# Розміри ігрового поля
WIDTH, HEIGHT = 800, 600

# Швидкості
BALL_SPEED = 5
PADDLE_SPEED = 10

# Зворотний відлік перед стартом
COUNTDOWN_START = 3


class GameServer:
    def __init__(self, host='localhost', port=8082):
        # Створюємо TCP-сокет
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Прив'язуємо сервер до адреси і порту
        self.server.bind((host, port))

        # Сервер може прийняти максимум 2 гравців
        self.server.listen(2)
        print("🎮 Server started")

        # Словник клієнтів: 0 і 1 — ID гравців
        self.clients = {0: None, 1: None}

        # Статус підключення кожного гравця
        self.connected = {0: False, 1: False}

        # Lock — щоб потоки не ламали дані один одного
        self.lock = threading.Lock()

        # Початковий стан гри
        self.reset_game_state()

        # Подія звуку (удар, стіна тощо)
        self.sound_event = None

    """Скидає всю гру до початкового стану"""
    def reset_game_state(self):


        # Позиції ракеток (Y-координата)
        self.paddles = {0: 250, 1: 250}

        # Очки гравців
        self.scores = [0, 0]

        # М'яч
        self.ball = {
            "x": WIDTH // 2,
            "y": HEIGHT // 2,
            "vx": BALL_SPEED * random.choice([-1, 1]),
            "vy": BALL_SPEED * random.choice([-1, 1])
        }

        # Зворотний відлік
        self.countdown = COUNTDOWN_START

        # Прапори завершення гри
        self.game_over = False
        self.winner = None

    """Приймає керування від конкретного гравця"""
    def handle_client(self, pid):
        conn = self.clients[pid]
        try:
            while True:
                # Отримуємо команду від клієнта
                data = conn.recv(64).decode()

                with self.lock:
                    # Рух ракетки вгору
                    if data == "UP":
                        self.paddles[pid] = max(60, self.paddles[pid] - PADDLE_SPEED)

                    # Рух ракетки вниз
                    elif data == "DOWN":
                        self.paddles[pid] = min(HEIGHT - 100, self.paddles[pid] + PADDLE_SPEED)

        except:
            # Якщо клієнт відключився
            with self.lock:
                self.connected[pid] = False
                self.game_over = True
                self.winner = 1 - pid  # автоматично виграє інший
                print(f"Гравець {pid} відключився. Переміг гравець {1 - pid}.")

    """Надсилає стан гри всім підключеним клієнтам"""
    def broadcast_state(self):
        state = json.dumps({
            "paddles": self.paddles,
            "ball": self.ball,
            "scores": self.scores,
            "countdown": max(self.countdown, 0),
            "winner": self.winner if self.game_over else None,
            "sound_event": self.sound_event
        }) + "\n"

        for pid, conn in self.clients.items():
            if conn:
                try:
                    conn.sendall(state.encode())
                except:
                    self.connected[pid] = False

    """Головна логіка руху м'яча"""
    def ball_logic(self):
        # Зворотний відлік перед початком гри
        while self.countdown > 0:
            time.sleep(1)
            with self.lock:
                self.countdown -= 1
                self.broadcast_state()

        # Основний ігровий цикл
        while not self.game_over:
            with self.lock:
                # Рух м'яча
                self.ball['x'] += self.ball['vx']
                self.ball['y'] += self.ball['vy']

                # Відбивання від верхньої і нижньої стін
                if self.ball['y'] <= 60 or self.ball['y'] >= HEIGHT:
                    self.ball['vy'] *= -1
                    self.sound_event = "wall_hit"

                # Зіткнення з ракетками
                if (self.ball['x'] <= 40 and
                    self.paddles[0] <= self.ball['y'] <= self.paddles[0] + 100) or \
                   (self.ball['x'] >= WIDTH - 40 and
                    self.paddles[1] <= self.ball['y'] <= self.paddles[1] + 100):
                    self.ball['vx'] *= -1
                    self.sound_event = "platform_hit"

                # Гол для гравця 1
                if self.ball['x'] < 0:
                    self.scores[1] += 1
                    self.reset_ball()

                # Гол для гравця 0
                elif self.ball['x'] > WIDTH:
                    self.scores[0] += 1
                    self.reset_ball()

                # Перевірка переможця
                if self.scores[0] >= 10:
                    self.game_over = True
                    self.winner = 0
                elif self.scores[1] >= 10:
                    self.game_over = True
                    self.winner = 1

                # Надсилаємо оновлений стан гри
                self.broadcast_state()

                # Скидаємо подію звуку
                self.sound_event = None

            # ~60 FPS
            time.sleep(0.016)

    """Скидає м'яч у центр після голу"""
    def reset_ball(self):
        self.ball = {
            "x": WIDTH // 2,
            "y": HEIGHT // 2,
            "vx": BALL_SPEED * random.choice([-1, 1]),
            "vy": BALL_SPEED * random.choice([-1, 1])
        }

    """Очікує підключення двох гравців"""
    def accept_players(self):
        for pid in [0, 1]:
            print(f"Очікуємо гравця {pid}...")
            conn, _ = self.server.accept()
            self.clients[pid] = conn

            # Надсилаємо гравцю його ID
            conn.sendall((str(pid) + "\n").encode())
            self.connected[pid] = True

            print(f"Гравець {pid} приєднався")

            # Запускаємо потік обробки клієнта
            threading.Thread(
                target=self.handle_client,
                args=(pid,),
                daemon=True
            ).start()

    """Головний цикл сервера"""
    def run(self):
        while True:
            # Чекаємо гравців
            self.accept_players()

            # Скидаємо гру
            self.reset_game_state()

            # Запускаємо логіку м'яча
            threading.Thread(
                target=self.ball_logic,
                daemon=True
            ).start()

            # Чекаємо завершення гри
            while not self.game_over and all(self.connected.values()):
                time.sleep(0.1)

            print(f"Гравець {self.winner} переміг!")
            time.sleep(5)

            # Закриваємо старі з'єднання
            for pid in [0, 1]:
                try:
                    self.clients[pid].close()
                except:
                    pass

                self.clients[pid] = None
                self.connected[pid] = False


# Запуск сервера
GameServer().run()
