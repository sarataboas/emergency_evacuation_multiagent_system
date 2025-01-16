import spade
import asyncio
import random
from fire import Fire
import heapq

class Environment:
    def __init__(self):

        self.building_map = [
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 'E', 1, 1, 1],
            [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1],
            [1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1],
            [1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1],
            [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 'E'],
            [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            [1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1],
            ['E', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            [1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1],
            [1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1],
            [1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1],
            [1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1],
            [1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1],
            [1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1],
            [1, 1, 1, 'E', 1, 1, 1, 1, 1, 1, 'E', 1, 1, 1, 1]
        ]



        self.fire = None
        self.agent_positions = {}  # Dicionário para mapear posições para JIDs
        self.exits = [
            (r, c)
            for r in range(len(self.building_map))
            for c in range(len(self.building_map[0]))
            if self.building_map[r][c] == 'E'
        ]
        self.building_exits = [
            (r, c)
            for r in range(len(self.building_map))
            for c in range(len(self.building_map[0]))
            if self.building_map[r][c] == 'E'
        ]
        self.fireman_called = False
        self.end = False

    # Começar o incêndio no ambiente
    async def start_fire(self):
        if self.fire is None:
            self.fire = Fire(self)
            asyncio.create_task(self.fire.continuous_spread())
        else:
            print("O fogo já está ativo no ambiente.")

    def is_transitable(self, position, ignore_agents=False):
        x, y = position
        if 0 <= x < len(self.building_map) and 0 <= y < len(self.building_map[0]):
            # Ignora agentes (2) apenas durante o cálculo da rota
            if ignore_agents:
                return self.building_map[x][y] in [0,'E',2,3,6,4, 'W', 5]
            # Não permitir mover para células ocupadas por agentes durante o movimento
            return self.building_map[x][y] in [0,'E',2,3,6, 'W', 5]
        return False

    def reached_exit(self, position):
        x, y = position
        return self.building_map[x][y] == 'E'

    def display_map(self):
        for row in self.building_map:
            print(' '.join(map(str, row)))

    def get_random_location(self):
        open_positions = []
        for i, row in enumerate(self.building_map):
            for j, cell in enumerate(row):
                if cell == 0:
                    open_positions.append((i, j))

        if not open_positions:
            raise ValueError("Nenhuma posição aberta disponível!")
        random_location = random.choice(open_positions)

        return random_location

    def update_agent_position(self, old_position, new_position, agent_id, agent_jid=None):

        # Limpar posição antiga
        if old_position:

            if self.building_map[old_position[0]][old_position[1]] != 'E':
                self.building_map[old_position[0]][old_position[1]] = 0
            # Remover a posição antiga do dicionário
            if old_position in self.agent_positions:
                del self.agent_positions[old_position]

        # Atualizar nova posição com o ID do agente
        if self.building_map[new_position[0]][new_position[1]] != 'E':

            self.building_map[new_position[0]][new_position[1]] = agent_id

        # Atualizar o dicionário com a nova posição e o JID do agente
        if agent_jid:
            self.agent_positions[new_position] = agent_jid



    def get_agent_jid_at_position(self, position):
        """
        Retorna o JID do agente na posição especificada, se existir.

        Args:
            position (tuple): Coordenadas (x, y) da posição.

        Returns:
            str: JID do agente na posição, ou None se não houver agente.
        """
        return self.agent_positions.get(position)

    def update_exits(self):
        """Verifica se o fogo está próximo de uma saída."""
        fire_positions = [
            (i, j)
            for i, row in enumerate(self.building_map)
            for j, cell in enumerate(row)
            if cell == 4
        ]

        for fire_pos in fire_positions:
            for exit_pos in self.exits:
                # Calcula a distância de Manhattan
                distance = self.dijkstra_step(fire_pos, exit_pos)
                if distance and distance <= 4:  # Verifica se está a uma célula de distância
                    self.exits.remove(exit_pos)
                    self.building_map[exit_pos[0]][exit_pos[1]] = 'C'

    def dijkstra_step(self, start, goal):
        distances = {start: 0}
        previous_nodes = {start: None}
        priority_queue = [(0, start)]

        while priority_queue:
            current_distance, current_position = heapq.heappop(priority_queue)

            if current_position == goal:
                path = []
                while current_position is not None:
                    path.append(current_position)
                    current_position = previous_nodes[current_position]
                path.reverse()
                return len(path)

            for neighbor in self.get_neighbors(current_position):
                # Ignorar agentes durante o cálculo do caminho
                if self.is_transitable(neighbor, ignore_agents=True):
                    distance = current_distance + 1
                    if neighbor not in distances or distance < distances[neighbor]:
                        distances[neighbor] = distance
                        previous_nodes[neighbor] = current_position
                        heapq.heappush(priority_queue, (distance, neighbor))

        return None

    def get_neighbors(self, position):
        x, y = position
        neighbors = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            new_x, new_y = x + dx, y + dy
            if self.is_transitable((new_x, new_y)):
                neighbors.append((new_x, new_y))
        return neighbors