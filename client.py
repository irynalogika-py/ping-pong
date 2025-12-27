from pygame import *          # бібліотека для гри (вікно, події, графіка)
import socket                 # для зʼєднання з сервером
import json                   # для розбору даних від сервера
from threading import Thread  # потік для прийому даних

# розміри вікна
WIDTH, HEIGHT = 800, 600

init()  # ініціалізація pygame
screen = display.set_mode((WIDTH, HEIGHT))  # створення вікна
clock = time.Clock()  # таймер FPS
display.set_caption("Пінг-Понг")  # заголовок вікна

# завантажуємо картинку для фону
main_background = image.load("images/b1.jpg").convert()
main_background = transform.scale(main_background, (WIDTH, HEIGHT))
bg_y = 0
bg_speed = 0.5  # швидкість руху фону

#  фон для перемоги та поразки
win_bg = image.load("images/win_bg.png").convert()
lose_bg = image.load("images/lose_bg.png").convert()
win_bg = transform.scale(win_bg, (WIDTH, HEIGHT))
lose_bg = transform.scale(lose_bg, (WIDTH, HEIGHT))

mixer.init()  # ініціалізація звукової системи

wall_sound = mixer.Sound("wall_hit.wav")        # звук удару об стіну
platform_sound = mixer.Sound("platform_hit.wav")  # звук удару об ракетку
wall_sound.set_volume(0.5)        # гучність (0.0 – 1.0)
platform_sound.set_volume(0.6)

def connect_to_server():
    # пробуємо підключитися, поки не вийде
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # створюємо сокет
            client.connect(('localhost', 8081))  # підключення до сервера

            buffer = ""        # буфер для отриманих даних
            game_state = {}    # стан гри

            # сервер надсилає ID гравця (0 або 1)
            my_id = int(client.recv(24).decode())

            return my_id, game_state, buffer, client
        except:
            pass  # якщо сервер недоступний — пробуємо ще раз


def receive():
    # окремий потік, який постійно читає дані з сервера
    global buffer, game_state, game_over

    while not game_over:
        try:
            data = client.recv(1024).decode()  # отримуємо дані
            buffer += data                     # додаємо в буфер

            # сервер надсилає пакети, розділені переносом рядка
            while "\n" in buffer:
                packet, buffer = buffer.split("\n", 1)

                if packet.strip():             # якщо пакет не порожній
                    game_state = json.loads(packet)  # перетворюємо JSON у dict
        except:
            game_state["winner"] = -1  # сервер зник
            break


font_win = font.Font(None, 72)   # великий шрифт (перемога)
font_main = font.Font(None, 36)  # основний шрифт

game_over = False
winner = None
you_win = None

# підключаємось до сервера
my_id, game_state, buffer, client = connect_to_server()

# запускаємо потік прийому даних
Thread(target=receive, daemon=True).start()

while True:
    for e in event.get():
        if e.type == QUIT:
            exit()  # вихід з гри

    # якщо йде зворотний відлік
    if "countdown" in game_state and game_state["countdown"] > 0:
        screen.fill((0, 0, 0))

        countdown_text = font.Font(None, 72).render(
            str(game_state["countdown"]), True, (255, 255, 255)
        )
        screen.blit(countdown_text, (WIDTH // 2 - 20, HEIGHT // 2 - 30))
        display.update()
        continue  # не малюємо гру

    # якщо гра завершилась
    if "winner" in game_state and game_state["winner"] is not None:
        screen.fill((20, 20, 20))

        if you_win is None:  # визначаємо результат лише один раз
            you_win = (game_state["winner"] == my_id)

        if you_win:
            screen.blit(win_bg, (0, 0))
        else:
            screen.blit(lose_bg, (0, 0))

        text = "Ти переміг!" if you_win else "Пощастить наступним разом!"
        win_text = font_win.render(text, True, (255, 215, 0))
        screen.blit(win_text, win_text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        restart_text = font_win.render("К - рестарт", True, (255, 215, 0))
        screen.blit(restart_text, restart_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 120)))

        display.update()
        continue  # блокуємо гру

    # якщо є стан гри — малюємо
    if game_state:
        # screen.fill((30, 30, 30))
        # screen.blit(background, (0, 0), )  # ← фон

        bg_y += bg_speed
        if bg_y >= HEIGHT:
            bg_y = 0

        screen.blit(main_background, (0, bg_y))
        screen.blit(main_background, (0, bg_y - HEIGHT))

        # ліва ракетка
        draw.rect(screen, (0, 255, 0),
                  (20, game_state['paddles']['0'], 20, 100))

        # права ракетка
        draw.rect(screen, (255, 0, 255),
                  (WIDTH - 40, game_state['paddles']['1'], 20, 100))

        # мʼяч
        draw.circle(screen, (255, 255, 255),
                    (game_state['ball']['x'], game_state['ball']['y']), 10)

        # рахунок
        score_text = font_main.render(
            f"{game_state['scores'][0]} : {game_state['scores'][1]}",
            True, (255, 255, 255)
        )
        screen.blit(score_text, (WIDTH // 2 - 25, 20))

        # події звуку
        if game_state['sound_event'] == 'wall_hit':
            wall_sound.play()
        elif game_state['sound_event'] == 'platform_hit':
            platform_sound.play()

    else:
        # якщо ще немає даних
        waiting_text = font_main.render("Очікування гравців...", True, (255, 255, 255))
        screen.blit(waiting_text, (WIDTH // 2 - 120, HEIGHT // 2))

    display.update()
    clock.tick(60)  # обмеження FPS

    # # керування ракеткою
    # keys = key.get_pressed()
    # if keys[K_w]:
    #     client.send(b"UP")
    # elif keys[K_s]:
    #     client.send(b"DOWN")

    # керування ракеткою мишкою
    mouse_y = mouse.get_pos()[1]  # поточна Y-координата миші

    # поточна позиція нашої ракетки з сервера
    if game_state and 'paddles' in game_state:
        paddle_y = game_state['paddles'][str(my_id)] + 50  # центр ракетки

        if mouse_y < paddle_y - 5:
            client.send(b"UP")  # мишка вище — рухаємося вгору
        elif mouse_y > paddle_y + 5:
            client.send(b"DOWN")  # мишка нижче — рухаємося вниз

