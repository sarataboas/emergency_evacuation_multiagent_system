from http.client import responses

import spade
import asyncio
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from collections import deque
import heapq
import math
from spade.template import Template

class SecurityAgent(spade.agent.Agent):

    async def setup(self):

        self.location = None
        self.mobility = 1
        self.environment = None
        self.id = 6
        self.state = 'Patrolling' # Patrolling,Exiting
        # possíveis comportamentos dos seguranças
        self.occupant_agents = []
        self.fireman_agents = []
        self.fire_coords = None
        self.alarm_activated = False
        self.help_requester_position = None
        self.evacuated = False

        # Comportamentos dos seguranças

        resposta_behaviour = self.Resposta()
        self.add_behaviour(resposta_behaviour)

        print(f"Agente de Segurança {self.id} configurado e aguardando para ser inicializado")

    async def set_attributes(self, location, environment):
        self.location = location
        self.environment = environment
        self.environment.update_agent_position(None, self.location, self.id, self.jid)

    def calculate_patrol_route(self):
        #Gerar 4 posicoes aleatorios do mapa

        posicoes = []
        for i in range(1): # numero de seguranças inicializados
            pos = self.environment.get_random_location()
            if pos != 1 or pos != 4 or pos != 'E':
                posicoes.append(pos)


        current_position = self.location
        full_route = []
        for target in posicoes:
            # Use Dijkstra to calculate the path to the target
            path = self.dijkstra_step(current_position, target)
            if path is not None:
                full_route.extend(path)  # Add the path to the full route
                current_position = target  # Update the current position
            else:
                print(f"No path found to target: {target}")

        return full_route

    def dijkstra_step(self, start, goal,flag=0):
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

                return path[1:]  # Retorna o caminho sem a posição inicial

            if flag == 1:
                for neighbor in self.get_neighbors(current_position,1):

                    if self.environment.is_transitable(neighbor, ignore_agents=True):
                        distance = current_distance + 1
                        if neighbor not in distances or distance < distances[neighbor]:
                            distances[neighbor] = distance
                            previous_nodes[neighbor] = current_position
                            heapq.heappush(priority_queue, (distance, neighbor))
            elif flag == 0:
                for neighbor in self.get_neighbors(current_position, 0):
                    if self.environment.is_transitable(neighbor, ignore_agents=False):
                        distance = current_distance + 1
                        if neighbor not in distances or distance < distances[neighbor]:
                            distances[neighbor] = distance
                            previous_nodes[neighbor] = current_position
                            heapq.heappush(priority_queue, (distance, neighbor))


        return None

    def get_neighbors(self, position, flag=0):
        x, y = position
        neighbors = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            new_x, new_y = x + dx, y + dy

            if flag == 1:
                if self.environment.is_transitable((new_x, new_y),1):
                    neighbors.append((new_x, new_y))
            elif flag == 0:
                if self.environment.is_transitable((new_x, new_y),0):
                    neighbors.append((new_x, new_y))
        return neighbors


    def calculate_helping_route(self, position):
        path = self.dijkstra_step(self.location, position)
        return path

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

    def get_best_exit(self,position):
        exits = self.environment.exits

        min_distance = 100000000
        best_exit = None
        for exit in exits:

            path = self.dijkstra_step(position, exit)

            if path:
                if len(path) < min_distance:
                    min_distance = len(path)
                    best_exit = exit

        return best_exit

    def calculate_exiting_route(self):
        exits = self.environment.exits
        min_distance = 10000000
        best_path = None
        for exit in exits:
            path = self.dijkstra_step(self.location, exit)
            if path:
                if len(path) < min_distance:
                    min_distance = len(path)
                    best_exit = exit
                    best_path = self.dijkstra_step(self.location, best_exit)

        return best_path

    def check_fire(self):
        for fire in self.fire_coords:

            path = self.dijkstra_step(self.location, fire, 1)

            if path and len(path) <= 3:

                self.state = 'Exiting'
                return
        return None


    class PatrolBehaviour(CyclicBehaviour):
        def __init__(self):
            super().__init__()
            self.patrol_route = None

        async def run(self):

            if self.patrol_route == None:
                self.patrol_route = self.agent.calculate_patrol_route()


            self.agent.check_fire()



            if self.agent.state == 'Patrolling':
                await self.agent.find_occupant()


                if len(self.patrol_route) > 0:
                    next_position = self.patrol_route.pop(0)
                else:
                    self.agent.state = 'Exiting'





            if self.agent.state == 'Exiting':
                await self.agent.find_occupant()
                exiting_route = self.agent.calculate_exiting_route()

                if self.agent.environment.reached_exit(self.agent.location):
                    self.agent.evacuated = True

                    await self.agent.stop()
                    return
                next_position = exiting_route.pop(0)




            if not self.agent.environment.is_transitable(next_position) and next_position != 'E':

                return
            self.agent.environment.update_agent_position(self.agent.location, next_position, self.agent.id, self.agent.jid)
            self.agent.location = next_position


            await asyncio.sleep(3)


    class Mandar_Coordenadas(spade.behaviour.OneShotBehaviour):
        def __init__(self, agent_jid, best_exit):
            super().__init__()
            self.agent_jid = agent_jid
            self.best_exit = best_exit

        async def run(self):



            msg = spade.message.Message(to=str(self.agent_jid))
            msg.body = "Mandar saida"

            msg.metadata = {"saida": str(self.best_exit)}
            await self.send(msg)



    async def find_occupant(self):

        occupants = []

        for i, row in enumerate(self.environment.building_map):
            for j, cell in enumerate(row):
                if cell == 2 or cell == 3:
                    occupants.append((i, j))

        for occupant in occupants:
            path = await self.has_line_of_sight(self.location, occupant)
            if path:
                best_exit = self.get_best_exit(occupant)
                agent_jid = self.environment.get_agent_jid_at_position(occupant)

                mandar_cords = self.Mandar_Coordenadas(agent_jid,best_exit)
                self.add_behaviour(mandar_cords)



    #pede ajuda a bombeiro
    class PedirSocorroBombeiros(spade.behaviour.OneShotBehaviour):
        def __init__(self, fireman, security):
            super().__init__()
            self.fireman = fireman
            self.security_jid = security
        async def run(self):
            msg = spade.message.Message(to=str(self.fireman))
            msg.body = "Socorro"
            msg.metadata = {"jid": str(self.security_jid)}
            await self.send(msg)



    class Resposta(spade.behaviour.CyclicBehaviour):
        def __init__(self, fireman=None):
            super().__init__()
            self.fireman = fireman

        async def run(self):
            message = await self.receive()

            if message:
                if 'alarm_activated' in message.body:
                    if not self.agent.alarm_activated:
                        self.agent.alarm_activated = True
                        patrol_behaviour = self.agent.PatrolBehaviour()
                        self.agent.add_behaviour(patrol_behaviour)

                    if "at" in message.body:


                        fire_coords_str = message.body.split(" at ")[1].strip()
                        self.agent.fire_coords = eval(fire_coords_str)  # Convert the string back to a list of tuples

                        if not self.agent.environment.fireman_called:
                            # seguranca efetua pedido de socorro aos bombeiros
                            fireman = self.agent.fireman_agents[0]

                            pedir_socorro_behaviour = self.agent.PedirSocorroBombeiros(fireman, self.agent.jid)
                            self.agent.add_behaviour(pedir_socorro_behaviour)

                            self.agent.environment.fireman_called = True

                    else:
                        print(f"Fire coordinates not found in the message.")

                elif message.body == "alarm_deactivated":
                    self.agent.alarm_active = False
                    # print(f"Security Agent {self.agent.id} received: Alarm deactivated")



