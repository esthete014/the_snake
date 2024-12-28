import pygame
import random
from typing import Final, Tuple, List, Set, Callable, Optional
from types import MappingProxyType
from abc import ABC, abstractmethod
from enum import Enum
import json

# Constants
SCREEN_WIDTH: Final = 640
SCREEN_HEIGHT: Final = 480
GRID_SIZE: Final = 20
GRID_WIDTH: Final = SCREEN_WIDTH // GRID_SIZE
GRID_HEIGHT: Final = SCREEN_HEIGHT // GRID_SIZE

UP: Final = (0, -1)
DOWN: Final = (0, 1)
LEFT: Final = (-1, 0)
RIGHT: Final = (1, 0)

DIRECTION_MAP: Final = MappingProxyType(
    {
        (pygame.K_UP, RIGHT): UP,
        (pygame.K_UP, LEFT): UP,
        (pygame.K_DOWN, RIGHT): DOWN,
        (pygame.K_DOWN, LEFT): DOWN,
        (pygame.K_LEFT, UP): LEFT,
        (pygame.K_LEFT, DOWN): LEFT,
        (pygame.K_RIGHT, UP): RIGHT,
        (pygame.K_RIGHT, DOWN): RIGHT,
    }
)

KEY_ACTIONS: Final = MappingProxyType(
    {
        pygame.K_UP: lambda snake: snake.update_direction(
            DIRECTION_MAP.get((pygame.K_UP, snake.direction))
        ),
        pygame.K_DOWN: lambda snake: snake.update_direction(
            DIRECTION_MAP.get((pygame.K_DOWN, snake.direction))
        ),
        pygame.K_LEFT: lambda snake: snake.update_direction(
            DIRECTION_MAP.get((pygame.K_LEFT, snake.direction))
        ),
        pygame.K_RIGHT: lambda snake: snake.update_direction(
            DIRECTION_MAP.get((pygame.K_RIGHT, snake.direction))
        ),
        pygame.K_ESCAPE: lambda game_state: (
            game_state.save_high_score(), pygame.quit(), exit()
        ),
        pygame.K_q: lambda game_state: game_state.update_speed(
            max(1, game_state.current_speed - 1)
        ),
        pygame.K_w: lambda game_state: game_state.update_speed(
            game_state.current_speed + 1
        ),
        pygame.K_a: lambda game_state: game_state.update_apple_count(1),
        pygame.K_s: lambda game_state: game_state.update_apple_count(-1),
        pygame.K_z: lambda game_state: game_state.update_rotten_apple_count(1),
        pygame.K_x: lambda game_state: game_state.update_rotten_apple_count(
            -1,
        ),
    }
)

BOARD_BACKGROUND_COLOR: Final = (0, 0, 0)
BORDER_COLOR: Final = (93, 216, 228)
APPLE_COLOR: Final = (255, 0, 0)
ROTTEN_APPLE_COLOR: Final = (128, 0, 0)
OBSTACLE_COLOR: Final = (0, 0, 0)
SNAKE_COLOR: Final = (0, 255, 0)
SPEED: Final = 20
ALL_CELLS: Final = {
    (x, y) for x in range(GRID_WIDTH) for y in range(GRID_HEIGHT)
}
HIGH_SCORE_FILE: Final = 'high_score.json'
CENTER_POSITION: Final = (GRID_WIDTH // 2, GRID_HEIGHT // 2)

# Initialize Pygame
pygame.init()
screen: Final = pygame.display.set_mode(
    (SCREEN_WIDTH, SCREEN_HEIGHT), 0, 32,
)
clock: Final = pygame.time.Clock()


class FoodEffect(Enum):
    """Перечисление эффектов от еды."""

    GROW: str = 'grow'
    SHRINK: str = 'shrink'


class IDrawable(ABC):
    """Абстрактный базовый класс для всех отрисовываемых объектов."""

    @abstractmethod
    def draw(self, screen: pygame.Surface) -> None:
        """Абстрактный метод для отрисовки объекта на экране."""
        pass


class GameObject(IDrawable):
    """Базовый класс для всех игровых объектов."""

    def __init__(
            self,
            position: Tuple[int, int] = (0, 0),
            color: Tuple[int, int, int] = (0, 0, 0),
    ):
        self.position: Tuple[int, int] = position
        self.body_color: Tuple[int, int, int] = color

    def draw(self, screen: pygame.Surface) -> None:
        """Отрисовка объекта на экране."""
        rect = pygame.Rect(
            self.position[0] * GRID_SIZE,
            self.position[1] * GRID_SIZE,
            GRID_SIZE,
            GRID_SIZE,
        )
        pygame.draw.rect(screen, self.body_color, rect)
        pygame.draw.rect(screen, BORDER_COLOR, rect, 1)


class Food(GameObject, ABC):
    """Абстрактный базовый класс для всех видов еды."""

    def __init__(self, position: Tuple[int, int], color: Tuple[int, int, int]):
        super().__init__(position, color)

    def randomize_position(
        self, occupied_positions: Set[Tuple[int, int]]
    ) -> None:
        """Рандомизация позиции еды, избегая занятых позиций."""
        free_cells: Set[Tuple[int, int]] = ALL_CELLS - occupied_positions
        self.position: Tuple[int, int] = random.choice(tuple(free_cells))

    @abstractmethod
    def get_effect(self) -> FoodEffect:
        """Абстрактный метод для получения эффекта от еды."""
        pass


class Apple(Food):
    """Класс для яблока, которое увеличивает змею."""

    def __init__(self, position: Tuple[int, int] = (0, 0)):
        super().__init__(position, APPLE_COLOR)

    def get_effect(self) -> FoodEffect:
        """Возвращает эффект от яблока."""
        return FoodEffect.GROW


class RottenApple(Food):
    """Класс для гнилого яблока, которое уменьшает змею."""

    def __init__(self, position: Tuple[int, int]):
        super().__init__(position, ROTTEN_APPLE_COLOR)

    def get_effect(self) -> FoodEffect:
        """Возвращает эффект от гнилого яблока."""
        return FoodEffect.SHRINK


class Obstacle(GameObject):
    """Класс для препятствий, которые могут столкнуться с змеей."""

    def __init__(self, position: Tuple[int, int]):
        super().__init__(position, OBSTACLE_COLOR)


class Snake(GameObject):
    """Класс для змеи, которая движется по экрану и поедает еду."""

    def __init__(self):
        super().__init__(CENTER_POSITION, SNAKE_COLOR)
        self.positions: List[Tuple[int, int]] = [CENTER_POSITION]
        self.direction: Tuple[int, int] = RIGHT
        self._last: Tuple[int, int] = self.position
        self._removed_positions: Set[Tuple[int, int]] = set()
        self._effect_map: dict = {
            FoodEffect.GROW: self.grow,
            FoodEffect.SHRINK: self.shrink,
        }

    def reset(self) -> None:
        """Сброс позиции змеи."""
        self.positions: List[Tuple[int, int]] = [CENTER_POSITION]

    def update_direction(self, direction: Tuple[int, int]) -> None:
        """Обновление направления движения змеи."""
        if direction is None:
            return
        self.direction: Tuple[int, int] = direction

    def move(self) -> None:
        """Движение змеи."""
        head: Tuple[int, int] = self.positions[0]
        new_head: Tuple[int, int] = (
            (head[0] + self.direction[0]) % GRID_WIDTH,
            (head[1] + self.direction[1]) % GRID_HEIGHT,
        )

        self._last: Tuple[int, int] = self.positions[-1]
        self.positions.insert(0, new_head)
        self.positions.pop()
        self.teleport()

        if self.check_self_bite():
            self._removed_positions.update(self.positions[1:])
            self.positions: List[Tuple[int, int]] = [head]

    def draw(self, screen: pygame.Surface) -> None:
        """Отрисовка змеи на экране."""
        self.draw_cell(screen, self.positions[0], self.body_color)
        self.draw_cell(screen, self.positions[-1], self.body_color)
        self.draw_cell(screen, self._last, BOARD_BACKGROUND_COLOR, False)

        for position in self._removed_positions:
            self.draw_cell(screen, position, BOARD_BACKGROUND_COLOR, False)

        self._removed_positions.clear()

    def draw_cell(
        self,
        screen: pygame.Surface,
        position: Tuple[int, int],
        color: Tuple[int, int, int],
        draw_border: bool = True,
    ) -> None:
        """Отрисовка отдельной клетки змеи."""
        rect = pygame.Rect(
            position[0] * GRID_SIZE,
            position[1] * GRID_SIZE,
            GRID_SIZE,
            GRID_SIZE,
        )
        pygame.draw.rect(screen, color, rect)
        if draw_border:
            pygame.draw.rect(screen, BORDER_COLOR, rect, 1)

    def get_head_position(self) -> Tuple[int, int]:
        """Возвращает позицию головы змеи."""
        return self.positions[0]

    def check_collision(self, obstacles: List[Obstacle]) -> bool:
        """Проверка на столкновение змеи с препятствиями."""
        head: Tuple[int, int] = self.positions[0]
        if head in [obstacle.position for obstacle in obstacles]:
            return True
        return False

    def check_eat(self, food: Food) -> bool:
        """Проверка, съела ли змея еду."""
        head: Tuple[int, int] = self.positions[0]
        if head == food.position:
            return True
        return False

    def teleport(self) -> None:
        """Телепортация змеи при выходе за границы экрана."""
        head: Tuple[int, int] = self.positions[0]
        if head[0] < 0:
            self.positions[0] = (GRID_WIDTH - 1, head[1])
        elif head[0] >= GRID_WIDTH:
            self.positions[0] = (0, head[1])
        elif head[1] < 0:
            self.positions[0] = (head[0], GRID_HEIGHT - 1)
        elif head[1] >= GRID_HEIGHT:
            self.positions[0] = (head[0], 0)

    def check_self_bite(self) -> bool:
        """Проверка на самопоедание змеи."""
        if len(self.positions) > 1:
            head: Tuple[int, int] = self.positions[0]
            if head in self.positions[1:]:
                return True
        return False

    def grow(self) -> None:
        """Рост змеи."""
        self.positions.append(self._last)

    def shrink(self) -> None:
        """Уменьшение змеи."""
        if len(self.positions) > 1:
            self._last: Tuple[int, int] = self.positions.pop()
            self._removed_positions.add(self._last)

    def apply_effect(self, effect: FoodEffect) -> None:
        """Применение эффекта от еды."""
        self._effect_map[effect]()


class GameState:
    """Класс для управления состоянием игры."""

    def __init__(self):
        self.high_score: int = 0
        self.current_speed: int = SPEED
        self.apple_count: int = 1
        self.rotten_apple_count: int = 1

    def load_high_score(self) -> None:
        """Загрузка рекорда из файла."""
        try:
            with open(HIGH_SCORE_FILE, 'r') as file:
                self.high_score: int = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            self.high_score: int = 0

    def save_high_score(self) -> None:
        """Сохранение рекорда в файл."""
        with open(HIGH_SCORE_FILE, 'w') as file:
            json.dump(self.high_score, file)

    def update_speed(self, new_speed: int) -> None:
        """Обновление скорости игры."""
        self.current_speed: int = new_speed

    def update_apple_count(self, delta: int) -> None:
        """Обновление количества яблок."""
        self.apple_count: int = max(1, self.apple_count + delta)

    def update_rotten_apple_count(self, delta: int) -> None:
        """Обновление количества гнилых яблок."""
        self.rotten_apple_count: int = max(1, self.rotten_apple_count + delta)


def initialize_game(
    game_state: GameState,
) -> Tuple[Snake, List[Apple], List[RottenApple], List[Obstacle]]:
    """Инициализация игры: создание змеи, еды и препятствий."""
    snake: Snake = Snake()
    apples: List[Apple] = [
        Apple((
            random.randint(0, GRID_WIDTH - 1),
            random.randint(0, GRID_HEIGHT - 1),
        ))
        for _ in range(game_state.apple_count)
    ]
    rotten_apples: List[RottenApple] = [
        RottenApple((
            random.randint(0, GRID_WIDTH - 1),
            random.randint(0, GRID_HEIGHT - 1),
        ))
        for _ in range(game_state.rotten_apple_count)
    ]
    obstacles: List[Obstacle] = [
        Obstacle((
            random.randint(0, GRID_WIDTH - 1),
            random.randint(0, GRID_HEIGHT - 1),
        ))
        for _ in range(random.randint(1, 5))
    ]

    obstacle_positions: set = {obstacle.position for obstacle in obstacles}
    occupied_positions: Set[Tuple[int, int]] = (
        set(snake.positions) | obstacle_positions
    )

    for apple in apples:
        apple.randomize_position(occupied_positions)
        occupied_positions.add(apple.position)

    for rotten_apple in rotten_apples:
        rotten_apple.randomize_position(occupied_positions)
        occupied_positions.add(rotten_apple.position)

    return snake, apples, rotten_apples, obstacles


def _handle_events(snake: Snake, game_state: GameState) -> None:
    """Обработка событий игры."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game_state.save_high_score()
            pygame.quit()
        elif event.type == pygame.KEYDOWN:
            handle_keys(event, snake, game_state)


def _handle_food(
    snake: Snake,
    foods: List[Food],
    obstacle_position: set,
) -> None:
    """Обработка съеденной еды."""
    for food in foods:
        if snake.check_eat(food):
            snake.apply_effect(food.get_effect())
            occupied_positions: Set[Tuple[int, int]] = (
                set(snake.positions) | obstacle_position
            )
            food.randomize_position(occupied_positions)


def game_loop(
    snake: Snake,
    foods: List[Food],
    obstacles: List[Obstacle],
    game_state: GameState,
) -> None:
    """Основной игровой цикл."""
    while True:
        _handle_events(snake, game_state)

        for food in foods:
            food.draw(screen)
        for obstacle in obstacles:
            obstacle.draw(screen)
        snake.move()
        snake.draw(screen)

        if snake.check_collision(obstacles):
            print('Game Over: Collided with obstacle or self!')
            break

        _handle_food(
            snake,
            foods,
            {obstacle.position for obstacle in obstacles},
        )

        if len(snake.positions) > game_state.high_score:
            game_state.high_score: int = len(snake.positions)

        pygame.display.set_caption(
            f'Snake Game - High Score: {game_state.high_score} - '
            f'Speed: {game_state.current_speed} - '
            f'Apple Count: {game_state.apple_count} - '
            f'Rotten Apple Count: {game_state.rotten_apple_count}'
        )

        pygame.display.flip()
        clock.tick(game_state.current_speed)


def main() -> None:
    """Основная функция для запуска игры."""
    pygame.display.set_caption('Snake Game')

    game_state: GameState = GameState()
    game_state.load_high_score()

    while True:
        screen.fill(BOARD_BACKGROUND_COLOR)
        snake, apples, rotten_apples, obstacles = initialize_game(game_state)
        foods: List[Food] = apples + rotten_apples
        game_loop(snake, foods, obstacles, game_state)


def handle_keys(
    event: pygame.event.Event,
    snake: Snake,
    game_state: GameState,
) -> None:
    """Обработка нажатий клавиш."""
    action: Optional[Callable] = KEY_ACTIONS.get(event.key)
    if action is None:
        return
    if event.key in (
        pygame.K_UP,
        pygame.K_DOWN,
        pygame.K_LEFT,
        pygame.K_RIGHT,
    ):
        action(snake)
    else:
        action(game_state)


if __name__ == '__main__':
    main()
