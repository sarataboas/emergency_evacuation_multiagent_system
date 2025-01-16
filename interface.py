import pygame
import sys
import asyncio

# Cores
COLORS = {
    0: (255, 255, 255),  # Corredor
    1: (128, 128, 128),  # Parede
    2: (0, 0, 255),      # Agente tipo 2
    3: (0, 255, 0),      # Agente tipo 3
    4: (255, 0, 0),      # Fogo
    5: (255, 203, 219),  # Fireman
    6: (0, 0, 0),        # SecurityAgent
    'E': (255, 255, 0),# Saída
    'C': (255,165,0),
    'W': (224, 255, 255) # Water
}

TILE_SIZE = 40
FPS = 10

class Interface:
    def __init__(self, environment):
        pygame.init()
        pygame.font.init()  # Inicializar o módulo de fontes
        self.environment = environment
        self.rows = len(environment.building_map)
        self.cols = len(environment.building_map[0])
        self.screen = pygame.display.set_mode((self.cols * TILE_SIZE, self.rows * TILE_SIZE))
        pygame.display.set_caption("Simulação de Evacuação")
        self.font = pygame.font.SysFont('Arial', 20)  # Usar fonte Arial para garantir compatibilidade

    def draw_grid(self):
        for i in range(self.rows):
            for j in range(self.cols):
                cell_value = self.environment.building_map[i][j]
                color = COLORS.get(cell_value, (0, 0, 0))
                pygame.draw.rect(self.screen, color, (j * TILE_SIZE, i * TILE_SIZE, TILE_SIZE, TILE_SIZE))
                pygame.draw.rect(self.screen, (0, 0, 0), (j * TILE_SIZE, i * TILE_SIZE, TILE_SIZE, TILE_SIZE), 1)

                # Desenhar o número do agente na célula

    async def run(self):
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            self.screen.fill((0, 0, 0))
            self.draw_grid()
            pygame.display.flip()
            clock.tick(FPS)
            await asyncio.sleep(0)  # Permite que o asyncio faça trocas de contexto
