# fire.py
import asyncio
import random
import time


class Fire:
    def __init__(self, environment, buildingmanagement, spread_interval=3):
        self.environment = environment
        self.building_management = buildingmanagement
        self.spread_interval = spread_interval  # Intervalo em segundos entre cada propagação
        self.initial_fire_position = self.get_random_fire_start()
        self.fire_detected = False
        if self.initial_fire_position:
            self.environment.building_map[self.initial_fire_position[0]][self.initial_fire_position[1]] = 4
            print(f"🔥 Fogo iniciado na posição {self.initial_fire_position}")

            self.environment.display_map()


    def get_random_fire_start(self):
        possible_positions = [(i, j) for i, row in enumerate(self.environment.building_map)
                              for j, cell in enumerate(row) if cell == 0]
        if not possible_positions:
            return None
        return random.choice(possible_positions)

    async def continuous_spread(self):
        """Propaga o fogo continuamente em intervalos definidos e notifica o BuildingManagement."""
        while True:
            await asyncio.sleep(self.spread_interval)
            if not self.fire_detected:
                print("🚨 Incêndio detectado! Ativando o alarme.")

                await self.building_management.change_alarm()
                self.fire_detected = True  # Garante que o alarme só seja ativado uma vez

            self.spread()

    def spread(self):
        """Espalha o fogo para células vizinhas."""
        new_fire_positions = []
        print("🔥 Espalhando o fogo...")
        for i in range(len(self.environment.building_map)):
            for j in range(len(self.environment.building_map[i])):
                if self.environment.building_map[i][j] == 4:  # Célula com fogo
                    # Espalha o fogo para as células vizinhas
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        new_x, new_y = i + dx, j + dy
                        new_position = new_x, new_y
                        if self.environment.is_transitable(new_position):
                            if self.environment.building_map[new_x][new_y] == 0:
                                new_fire_positions.append((new_x, new_y))
                                self.environment.update_exits()

        for pos in new_fire_positions:
            self.environment.building_map[pos[0]][pos[1]] = 4
        print("🔥 O fogo se espalhou para novas posições.")
        #self.environment.display_map() #Desconfio que seja esta linha a multiplicar os prints :/



