import spade
import asyncio
import heapq
import math

from spade.behaviour import CyclicBehaviour

from environment import Environment


class OccupantAgent(spade.agent.Agent):
    async def setup(self):
        # Inicialização do agente
        self.location = None
        self.mobility = 1
        self.destination = (-1, -1)
        self.evacuated = False
        self.environment = None
        self.agent_id = 2
        self.is_alarm_activated = False
        self.knowlegde = 0
        self.path = []
        self.state = None
        self.helper_position = (-1,-1)
        self.requester_position = (-1,-1)
        self.dead = False

        # Atributos associados a criaçao de grupos
        alarm_behavior = self.AlarmListenerBehaviour()
        self.add_behaviour(alarm_behavior)



        resposta_security = self.Receber_Ajuda_Security()
        self.add_behaviour(resposta_security)

    async def set_attributes(self, location, mobility, environment, knowlegde):
        self.location = location
        self.knowlegde = knowlegde
        self.mobility = mobility
        if knowlegde == 1:
            self.agent_id = 2
            self.state = 'Waiting'
        else:
            self.agent_id = 3

        self.environment = environment
        self.environment.update_agent_position(None, self.location, self.agent_id, self.jid)
        self.destination = self.find_exit()

    class AlarmListenerBehaviour(spade.behaviour.CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                if msg.body == "alarm_activated":
                    self.agent.is_alarm_activated = True
                    #print(f"{self.agent.jid} recebeu o alarme de evacuação!")
                elif msg.body == "alarm_deactivated":
                    self.agent.is_alarm_activated = False
                    #print(f"{self.agent.jid} recebeu a desativação do alarme.")

    class NavigationBehaviour(spade.behaviour.CyclicBehaviour):
        async def run(self):
            if self.agent.is_alarm_activated and not self.agent.evacuated:
                await self.agent.navigate_to_exit()
                await asyncio.sleep(5)

    def find_exit(self):
        if self.agent_id == 3:
            exits = self.environment.building_exits

            min_distance = 100000000
            best_exit = None
            for exit in exits:
                path = self.dijkstra_step(self.location, exit)
                if path:

                    if len(path) < min_distance:
                        min_distance = len(path)
                        best_exit = exit
            return best_exit
        return None

    def is_dead(self):
        x, y = self.location
        directions = [
            (0, 1),  # Direita
            (0, -1),  # Esquerda
            (1, 0),  # Baixo
            (-1, 0),  # Cima
            (1, 1),
            (-1, 1),
            (1, -1),
            (-1, -1),
        ]

        # Verificar cada direção adjacente
        for dx, dy in directions:
            new_x, new_y = x + dx, y + dy
            if (0 <= new_x < len(self.environment.building_map)) and (
                    0 <= new_y < len(self.environment.building_map[0])):
                if self.environment.building_map[new_x][new_y] == 4 or self.environment.building_map[new_x][new_y] == 1:
                    return True

        # Se nenhuma saída adjacente for encontrada
        return False


    async def navigate_to_exit(self):

        new_position = None
        # Verificar se o agente já chegou à saída
        if self.environment.reached_exit(self.location):
            self.evacuated = True
            #print(f"Agente {self.jid} evacuou com sucesso o edifício!")
            await self.stop()
            return

        # Detectar fogo visível
        fire_positions = self.check_fire(self.location)
        #print("POSIÇOES DE FOGO: ", fire_positions)

        # Lógica para agentes com `knowlegde = 1` (agente tipo 2)
        if self.knowlegde == 1:


            if fire_positions:
                #print("Agente tipo 2 detectou fogo.")
                await self.find_security_perimeter()

                # Verificar se há uma saída adjacente
                adjacent_exit = self.find_adjacent_exit()
                if adjacent_exit:
                    #print(f"Agente tipo 2 encontrou uma saída adjacente em {adjacent_exit}, movendo-se para a saída.")
                    new_position = adjacent_exit
                else:
                    # Se não houver saída adjacente, mover-se para a posição mais distante do fogo
                    #print("Nenhuma saída adjacente encontrada, movendo-se para a posição mais segura.")
                    new_position = self.move_away_from_fire(fire_positions)

                self.destination = None



            else:
                # Se não houver fogo, seguir a lógica normal de encontrar a saída visível
                if self.state == 'Waiting':
                    await self.find_security_perimeter()

                    await self.find_exit_in_corridor()

                    await self.find_coleguinha_sabixao()


                if self.state == 'Locked In':
                    new_path = self.dijkstra_step(self.location, self.destination)
                    if new_path:
                        new_position = new_path.pop(0)

                if self.state == 'Following':
                    new_path = self.dijkstra_step(self.location, self.destination)
                    if new_path:
                        new_position = new_path.pop(0)

        else:

            if fire_positions:
                print("Agente tipo 3 detectou fogo, recalculando a rota usando Dijkstra.")
                self.destination = self.find_exit()  # Recalcular a saída
                new_path = self.dijkstra_step(self.location, self.destination)
                if new_path:
                    new_position = new_path.pop(0)
            else:
                new_path = self.dijkstra_step(self.location, self.destination)
                if new_path:
                    new_position = new_path.pop(0)
                #print(f"Destino  {self.destination} do {self.jid}")

        # Verificar se a nova posição é transitável
        if new_position and self.environment.is_transitable(new_position, ignore_agents=False):
            self.environment.update_agent_position(self.location, new_position, self.agent_id,self.jid)
            self.location = new_position

            # Verificar se o agente chegou à saída
            if self.environment.reached_exit(self.location):
                self.evacuated = True
                #print(f"Agente {self.jid} evacuou com sucesso o edifício!")
                await self.stop()

            #print(f"{self.jid} avançou para {self.location}.")
        else:
            #print(f"{self.jid} não conseguiu avançar devido a colisão ou obstáculo.")
            await asyncio.sleep(2)

        if self.is_dead():
            self.dead = True


    def find_adjacent_exit(self):
        x, y = self.location
        directions = [
            (0, 1),  # Direita
            (0, -1),  # Esquerda
            (1, 0),  # Baixo
            (-1, 0),  # Cima
            (1, 1),
            (-1, 1),
            (1, -1),
            (-1, -1),
        ]

        # Verificar cada direção adjacente
        for dx, dy in directions:
            new_x, new_y = x + dx, y + dy
            if (0 <= new_x < len(self.environment.building_map)) and (
                    0 <= new_y < len(self.environment.building_map[0])):
                if self.environment.building_map[new_x][new_y] == 'E':
                    return (new_x, new_y)

        # Se nenhuma saída adjacente for encontrada
        return None

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
                return path[1:]

            for neighbor in self.get_neighbors(current_position):
                # Ignorar agentes durante o cálculo do caminho
                if self.environment.is_transitable(neighbor, ignore_agents=False):
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
            if self.environment.is_transitable((new_x, new_y)):
                neighbors.append((new_x, new_y))
        return neighbors

    def euclidean_distance(self, start, goal):
        x1, y1 = start
        x2, y2 = goal
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    """ Vamos definir uma funçao para os agentes ocupantes com menor nivel de conhecimento do edificio deslocarem-se em
    direçao a saida, quando a vem
    Para isso, vamos utilizar o algoritmo de Bresenham, que considera linhas horizontais, verticais e diagonais.
    Dessa forma, o que a funçao faz e:
     -> primeiro calcular todas as saidas.
     -> Calcula a linha para cada saida, com a funçao "has_line_of_sight e ve se e visivel"""

    async def find_exit_in_corridor(self):
        x, y = self.location
        saidas = []

        for i, row in enumerate(self.environment.building_map):
            for j, cell in enumerate(row):
                if cell == 'E':
                    saidas.append((i, j))

        for saida in saidas:
            path = await self.has_line_of_sight(self.location, saida)
            if path:

                self.destination = saida

                self.state = 'Locked In'
                return saida

        # Se nenhuma saída for encontrada, definir self.path como lista vazia
        self.path = []
        return None

    async def has_line_of_sight(self, location, saida):
        x0, y0 = location
        x1, y1 = saida
        path = []

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:

            # Se encontrar um obstáculo ou fogo, retorna uma lista vazia
            if self.environment.building_map[x0][y0] == 1 or self.environment.building_map[x0][y0] == 4:
                return []

            # Se chegar ao ponto final (saída), retorna o caminho
            if (x0, y0) == (x1, y1):
                return path

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
            # Adicionar a posiçao ao caminho
            path.append((x0, y0))

    def check_fire(self, position):
        rows, cols = len(self.environment.building_map), len(self.environment.building_map[0])
        fire_positions = []  # List to store the JIDs of occupants found

        # Iterate through a 3x3 grid centered on the position
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if dx == 0 and dy == 0:
                    continue  # Skip the center position (security's own position)

                neighbor = (position[0] + dx, position[1] + dy)

                # Check if the neighbor is within the map bounds
                if 0 <= neighbor[0] < rows and 0 <= neighbor[1] < cols:
                    # Check if the cell contains an occupant (2 or 3)
                    if self.environment.building_map[neighbor[0]][neighbor[1]]==4:
                        fire_positions.append(neighbor)

        return fire_positions

    # Fugir do fogo
    def move_away_from_fire(self, fire_positions):
        x, y = self.location
        best_position = self.location
        max_distance = -1

        # Direções possíveis para mover
        directions = [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1)
        ]

        # Verificar cada posição adjacente

        for dx, dy in directions:

            new_x, new_y = x + dx, y + dy

            # Verificar se a posição é transitável
            if self.environment.is_transitable((new_x, new_y)):
                # Calcular a distância mínima para todos os focos de fogo
                min_distance = min(
                    self.euclidean_distance((new_x, new_y), fire_pos) for fire_pos in fire_positions
                )

                # Escolher a posição com a maior distância mínima
                if min_distance > max_distance:
                    max_distance = min_distance
                    best_position = (new_x, new_y)

        #print(f"Movendo-se para a posição mais distante do fogo: {best_position}")

        return best_position

    async def find_coleguinha_sabixao(self):
        x, y = self.location
        coleguinhas = []

        for i, row in enumerate(self.environment.building_map):
            for j, cell in enumerate(row):
                if cell == 3:
                    coleguinhas.append((i, j))

        for coleguinha in coleguinhas:
            path = await self.has_line_of_sight(self.location, coleguinha)
            #print("Caminho para o Coleguinha:", path)

            if path:
                #print("Posiçao do Amigo: ", coleguinha)
                amigo = self.environment.get_agent_jid_at_position(coleguinha) #Isto devia retornar um agent_jid
                #print("O que e o Amigo:", amigo)
                #print("Self_destination - FIND_COLEGUINHA do jid : ", self.destination , self.jid)

                if self.destination == None:
                    await self.pedir_ajuda(amigo)
                    #print(f"{self.jid} vê o coleguinha em {coleguinha}!")
                    return


        # Se nenhuma saída for encontrada, definir self.path como lista vazia
        return None

    async def pedir_ajuda(self, amigo):
        pedir_ajuda_task = self.PedirAjudaBehaviour(amigo)
        self.add_behaviour(pedir_ajuda_task)


    class PedirAjudaBehaviour(spade.behaviour.OneShotBehaviour):
        def __init__(self, coleguinha):
            super().__init__()
            self.coleguinha = coleguinha

        async def run(self):
            msg = spade.message.Message(to=str(self.coleguinha))
            msg.body = "Ajuda ao colega"
            msg.metadata = {"position": str(self.agent.location)}
            await self.send(msg)



    async def find_security_perimeter(self):
        rows, cols = len(self.environment.building_map), len(self.environment.building_map[0])
           # List to store the JIDs of occupants found

        # Iterate through a 3x3 grid centered on the position
        for dx in range(-3, 4):  # Offsets: -1, 0, 1 for rows
            for dy in range(-3, 4):  # Offsets: -1, 0, 1 for columns
                if dx == 0 and dy == 0:
                    continue  # Skip the center position (security's own position)

                neighbor = (self.location[0] + dx, self.location[1] + dy)

                # Check if the neighbor is within the map bounds
                if 0 <= neighbor[0] < rows and 0 <= neighbor[1] < cols:
                    # Check if the cell contains an occupant (2 or 3)
                    if self.environment.building_map[neighbor[0]][neighbor[1]] == 5:
                        jid_at_pos = self.environment.get_agent_jid_at_position(neighbor)
                        if jid_at_pos:
                            if self.destination == None:
                                ask_security_help = self.Pedir_Ajuda_Security(jid_at_pos)
                                self.add_behaviour(ask_security_help)
                                return



    class Pedir_Ajuda_Security(spade.behaviour.OneShotBehaviour):
        def __init__(self,seguranca):
            super().__init__()
            self.seguranca = seguranca

        async def run(self):
            msg = spade.message.Message(to=str(self.seguranca))
            msg.body = "Ajuda"
            msg.metadata = {"position": str(self.agent.location)}
            await self.send(msg)


    class Receber_Ajuda_Security(spade.behaviour.CyclicBehaviour):
        async def run(self):
            msg = await self.receive()
            if msg and msg.body == 'Mandar saida':
                exit_position = eval(msg.metadata.get("saida","(-1,-1)"))

                self.agent.state = 'Following'
                self.agent.destination = exit_position

            elif msg and msg.body == 'Ajuda ao colega':
                requester_position = eval(msg.metadata.get("position", "(-1, -1)"))


                # Responder com a posição da saída
                response = spade.message.Message(to=str(msg.sender))
                response.body = "Vou ajudar"
                response.metadata = {
                    "position": str(self.agent.location),
                    "exit": str(self.agent.destination)  # Enviar a posição da saída
                }
                await self.send(response)


            elif msg and msg.body == "Vou ajudar":
                exit_position = eval(msg.metadata.get("exit", "(-1, -1)"))
                self.destination = exit_position
                self.agent.state = 'Following'
